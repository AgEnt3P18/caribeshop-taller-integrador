"""Analisis de P2 a partir del monitor (10 req/s) y del T0 de la falla.

python scripts/p2_analyze.py evidencias/p2_logica_monitor.csv evidencias/p2_logica_t0.txt <hostname_afectado> [instances.tsv]
"""
import csv
import re
import sys
import datetime as dt

mon, t0file, host = sys.argv[1], sys.argv[2], sys.argv[3]
inst_tsv = sys.argv[4] if len(sys.argv) > 4 else None
t0 = float(re.search(r"T0_EPOCH=([\d.]+)", open(t0file, encoding="utf-8").read()).group(1))
rows = [dict(r, ts=float(r["ts"])) for r in csv.DictReader(open(mon, encoding="utf-8"))]

pre = [r for r in rows if r["ts"] < t0]
post = [r for r in rows if r["ts"] >= t0]
fail = lambda rs: sum(1 for r in rs if r["status"] != "200")  # noqa: E731

print(f"T0 = {dt.datetime.fromtimestamp(t0, dt.timezone.utc):%H:%M:%S.%f} UTC")
print(f"Linea base (antes de T0): {len(pre)} peticiones, {fail(pre)} fallidas ({100*fail(pre)/max(1,len(pre)):.2f} %)")

last_hit = max((r["ts"] for r in post if r["instance"] == host), default=None)
if last_hit:
    print(f"Ultima respuesta de {host}: T0 + {last_hit - t0:.1f} s")
fails_post = [r for r in post if r["status"] != "200"]
if fails_post:
    print(f"Primera falla: T0 + {fails_post[0]['ts'] - t0:.1f} s; ultima falla: T0 + {fails_post[-1]['ts'] - t0:.1f} s")

# Ventana de falla: desde T0 hasta que el host deja de recibir trafico (o la ultima falla), lo que ocurra despues
end = max([t0 + 1] + ([last_hit] if last_hit else []) + [r["ts"] for r in fails_post if r["ts"] - t0 < 120])
win = [r for r in post if r["ts"] <= end]
print(f"Ventana de falla: {end - t0:.1f} s -> {len(win)} peticiones, {fail(win)} fallidas = {100*fail(win)/max(1,len(win)):.2f} % de error")
w60 = [r for r in post if r["ts"] <= t0 + 60]
print(f"Ventana fija de 60 s: {len(w60)} peticiones, {fail(w60)} fallidas = {100*fail(w60)/max(1,len(w60)):.2f} %")
print(f"Despues de T0 (total): {len(post)} peticiones, {fail(post)} fallidas = {100*fail(post)/max(1,len(post)):.2f} %")

hosts = {}
for r in post:
    if r["instance"]:
        hosts.setdefault(r["instance"], [r["ts"], r["ts"]])
        hosts[r["instance"]][1] = r["ts"]
for h, (a, b) in sorted(hosts.items()):
    print(f"  {h}: atiende de T0{a - t0:+.1f}s a T0{b - t0:+.1f}s")

if inst_tsv:
    print("Instancias (poll):")
    prev = None
    for line in open(inst_tsv, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        t = dt.datetime.fromisoformat(p[0].replace("Z", "+00:00")).timestamp()
        if t < t0 - 30:
            continue
        key = (p[1], p[2], p[3] if len(p) > 3 else "")
        if key != prev:
            print(f"  T0{t - t0:+7.0f}s total={p[1]} ok={p[2]} {p[3] if len(p) > 3 else ''}")
            prev = key
