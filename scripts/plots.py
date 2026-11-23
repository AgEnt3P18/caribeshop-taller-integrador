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


def capacity(src, dst, cpu=None):
    h = [r for r in read_hist(src) if r["p95"] is not None]
    steps = {}
    for r in h:
        steps.setdefault(r["users"], []).append(r)
    users = sorted(steps)
    rps = [st.mean(x["rps"] for x in steps[u]) for u in users]
    p95 = [st.median(x["p95"] for x in steps[u]) for u in users]
    p50 = [st.median(x["p50"] for x in steps[u]) for u in users]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(rps, p95, "-o", color=ORANGE, label="p95 (mediana del escalón)")
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
    inst = read_tsv(inst_tsv)
    cpu = read_tsv(cpu_tsv)
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
    fig.tight_layout()
    fig.savefig(dst)


def failure(src, dst, t_fail, title):
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    t0 = float(t_fail)
    buckets = {}
    for r in rows:
        s = int(float(r["ts"]) - t0)
        b = buckets.setdefault(s, {"ok": 0, "fail": 0, "inst": {}})
        if r["status"] == "200":
            b["ok"] += 1
            b["inst"][r["instance"]] = b["inst"].get(r["instance"], 0) + 1
        else:
            b["fail"] += 1
    secs = sorted(buckets)
    insts = sorted({i for b in buckets.values() for i in b["inst"]})
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bottom = [0] * len(secs)
    palette = [BLUE, GREEN, ORANGE, "#9333ea", "#0891b2"]
    for k, i in enumerate(insts):
        vals = [buckets[s]["inst"].get(i, 0) for s in secs]
        ax.bar(secs, vals, bottom=bottom, width=1.0, color=palette[k % len(palette)], label=i.replace("vmss-caribeshop", "inst "))
        bottom = [a + b for a, b in zip(bottom, vals)]
    ax.bar(secs, [buckets[s]["fail"] for s in secs], bottom=bottom, width=1.0, color=RED, label="fallidas")
    ax.axvline(0, color="black", ls="--", lw=1)
    ax.set_xlabel("Segundos desde la inyección de la falla")
    ax.set_ylabel("Peticiones / s")
    ax.set_title(title)
    ax.legend(loc="upper left", frameon=False, ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "capacity":
        capacity(sys.argv[2], sys.argv[3])
    elif mode == "staircase":
        staircase(*sys.argv[2:6])
    elif mode == "failure":
        failure(*sys.argv[2:6])
