"""Graficos del informe a partir de las evidencias (Locust + Azure Monitor + monitor de sonda).

python scripts/plots.py capacity  evidencias/p1_capacity_stats_history.csv evidencias/graficos/p1_capacidad.png [cpu.tsv]
python scripts/plots.py staircase evidencias/p1_staircase_stats_history.csv evidencias/graficos/p1_escalonado.png instances.tsv cpu.tsv
python scripts/plots.py failure   evidencias/p2_xxx_monitor.csv evidencias/graficos/p2_xxx.png <ts_falla_epoch> "titulo"
"""
import csv
import datetime as dt
import statistics as st
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, GREEN, RED, GRAY = "#2563eb", "#ea580c", "#16a34a", "#dc2626", "#6b7280"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 140})


def utc(ts):
    return dt.datetime.fromtimestamp(float(ts), dt.timezone.utc)


def read_hist(path):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["Name"] == "Aggregated"]
    out = []
    for r in rows:
        p95 = float(r["95%"]) if r["95%"] not in ("N/A", "") else None
        p50 = float(r["50%"]) if r["50%"] not in ("N/A", "") else None
        out.append({"t": utc(r["Timestamp"]), "users": int(r["User Count"]), "rps": float(r["Requests/s"]),
                    "fails": float(r["Failures/s"]), "p95": p95, "p50": p50})
    return out


def read_tsv(path):
    pts = []
    for line in open(path, encoding="utf-8"):
        parts = line.strip().split("\t")
        if len(parts) >= 2 and parts[1] not in ("None", ""):
            pts.append((dt.datetime.fromisoformat(parts[0].replace("Z", "+00:00")), float(parts[1])))
    return pts


def capacity(src, dst, src2=None):
    h = [r for r in read_hist(src) if r["p95"] is not None]
    if src2:  # segunda rampa (continua desde START_USERS): se descartan sus escalones de arranque
        top = max(r["users"] for r in h)
        h += [r for r in read_hist(src2) if r["p95"] is not None and r["users"] > top]
    steps = {}
    for r in h:
        steps.setdefault(r["users"], []).append(r)
    # se descartan las primeras muestras de cada escalon (transitorio del spawn)
    steps = {u: (rs[3:] if len(rs) > 6 else rs) for u, rs in steps.items()}
    users = sorted(steps)
    rps = [st.mean(x["rps"] for x in steps[u]) for u in users]
    p95 = [st.median(x["p95"] for x in steps[u]) for u in users]
    p50 = [st.median(x["p50"] for x in steps[u]) for u in users]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    art = [abs(v - 1200) < 1 and u < 170 for u, v in zip(users, p95)]  # RTO TCP 1 s + RTT
    ax.plot([x for x, a in zip(rps, art) if not a], [y for y, a in zip(p95, art) if not a], "-o", color=ORANGE,
            label="p95 (mediana del escalón)")
    ax.plot([x for x, a in zip(rps, art) if a], [y for y, a in zip(p95, art) if a], "o", mfc="white", mec=GRAY,
            label="p95 = 1,2 s: retransmisión SYN en la red del cliente")
    ax.plot(rps, p50, "-o", color=BLUE, ms=3, label="p50")
    ax.axhline(1000, color=RED, ls="--", lw=1, label="umbral 1 s")
    for u, x, y in zip(users, rps, p95):
        if u % 20 == 0:
            ax.annotate(f"{u} u", (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8, color=GRAY)
    ax.set_xlabel("Peticiones por segundo (RPS)")
    ax.set_ylabel("Latencia (ms)")
    ax.set_title("P1.1 Capacidad de una instancia (Standard_D2s_v4, autoscale min=max=1)")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(dst)
    print("tabla escalones:")
    for u, a, b, c in zip(users, rps, p50, p95):
        print(f"{u:4d} usuarios  {a:6.1f} rps  p50={b:6.0f}  p95={c:6.0f}")


def staircase(src, dst, inst_tsv, cpu_tsv):
    h = read_hist(src)
    t_start, t_end = h[0]["t"] - dt.timedelta(minutes=1), dt.datetime.fromtimestamp(h[-1]["t"].timestamp() + 600, dt.timezone.utc)
    inst = [p for p in read_tsv(inst_tsv) if t_start <= p[0] <= t_end]
    cpu = [p for p in read_tsv(cpu_tsv) if t_start <= p[0] <= t_end]
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.5), sharex=True)
    t = [r["t"] for r in h]
    axes[0].plot(t, [r["rps"] for r in h], color=BLUE, lw=1.2, label="RPS")
    axes[0].plot(t, [r["fails"] for r in h], color=RED, lw=1, label="Fallos/s")
    ax2 = axes[0].twinx()
    ax2.plot(t, [r["users"] for r in h], color=GRAY, lw=1, ls=":", label="Usuarios")
    ax2.set_ylabel("Usuarios")
    axes[0].set_ylabel("RPS")
    axes[0].legend(loc="upper left", frameon=False)
    axes[0].set_title("P1.2 Perfil escalonado: carga, latencia, CPU e instancias (UTC)")
    axes[1].plot(t, [r["p95"] if r["p95"] is not None else float("nan") for r in h], color=ORANGE, lw=1, label="p95")
    axes[1].plot(t, [r["p50"] if r["p50"] is not None else float("nan") for r in h], color=BLUE, lw=1, label="p50")
    axes[1].set_ylabel("Latencia (ms)")
    axes[1].set_yscale("log")
    axes[1].legend(loc="upper left", frameon=False)
    axes[2].plot([p[0] for p in cpu], [p[1] for p in cpu], color=GREEN, lw=1.4, label="CPU promedio VMSS (%)")
    axes[2].axhline(70, color=RED, ls="--", lw=0.8)
    axes[2].axhline(30, color=BLUE, ls="--", lw=0.8)
    axes[2].set_ylabel("CPU %")
    ax3 = axes[2].twinx()
    ax3.step([p[0] for p in inst], [p[1] for p in inst], where="post", color="black", lw=1.6, label="Instancias")
    ax3.set_ylabel("Instancias")
    ax3.set_ylim(0, 5)
    axes[2].legend(loc="upper left", frameon=False)
    ax3.legend(loc="upper right", frameon=False)
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[2].set_xlim(t_start, t_end)
    fig.tight_layout()
    fig.savefig(dst)


def failure(src, dst, t_fail, title, events="", bucket=5):
    """Peticiones/s por instancia y fallidas, en ventanas de `bucket` s alrededor de T0.
    events: "seg:etiqueta;seg:etiqueta" para marcar hitos."""
    from matplotlib.patches import Patch
    t0 = float(t_fail)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    bk = {}
    for r in rows:
        b = int((float(r["ts"]) - t0) // bucket) * bucket
        e = bk.setdefault(b, {})
        k = r["instance"].replace("vmss-caribeshop0000", "inst ") if r["status"] == "200" else "fallidas"
        e[k] = e.get(k, 0) + 1
    xs = sorted(bk)
    keys = sorted({k for v in bk.values() for k in v if k != "fallidas"}) + ["fallidas"]
    pal = [BLUE, GREEN, ORANGE, "#9333ea", "#0891b2"]
    colors = {k: (RED if k == "fallidas" else pal[i % len(pal)]) for i, k in enumerate(keys)}
    fig, ax = plt.subplots(figsize=(9, 3.6))
    bot = [0] * len(xs)
    for k in keys:
        v = [bk[x].get(k, 0) / bucket for x in xs]
        ax.bar(xs, v, bottom=bot, width=bucket, align="edge", color=colors[k], linewidth=0)
        bot = [a + b for a, b in zip(bot, v)]
    for i, ev in enumerate(e for e in events.split(";") if e):
        x, lab = ev.split(":", 1)
        ax.axvline(float(x), color="black", ls="--", lw=1)
        ax.text(float(x) + 4, 11.3 - 0.8 * (i % 2), lab, fontsize=8)
    ax.set_ylim(0, 12)
    ax.set_xlabel("Segundos desde la falla (T0)")
    ax.set_ylabel(f"Peticiones/s (prom. {bucket} s)")
    ax.set_title(title)
    ax.legend(handles=[Patch(color=colors[k], label=k) for k in keys], frameon=False, ncol=len(keys), fontsize=8, loc="lower center")
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "capacity":
        capacity(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif mode == "staircase":
        staircase(*sys.argv[2:6])
    elif mode == "failure":
        failure(*sys.argv[2:7])
