"""Monitor de disponibilidad para P2.

Envia N peticiones por segundo al balanceador y registra en CSV:
timestamp, codigo HTTP (0 = error de conexion), instancia que respondio (X-Instance), latencia.

Uso: python probe_monitor.py http://<fqdn>/ salida.csv --rate 5 --duration 600
"""
import argparse
import csv
import threading
import time
import urllib.error
import urllib.request


def one(url, timeout):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Connection": "close"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
            return t0, r.status, r.headers.get("X-Instance", ""), time.time() - t0, ""
    except urllib.error.HTTPError as e:
        return t0, e.code, e.headers.get("X-Instance", ""), time.time() - t0, "http"
    except Exception as e:  # noqa: BLE001
        return t0, 0, "", time.time() - t0, e.__class__.__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--rate", type=float, default=5)
    ap.add_argument("--duration", type=int, default=600)
    ap.add_argument("--timeout", type=float, default=3)
    a = ap.parse_args()

    rows, lock = [], threading.Lock()

    def worker():
        r = one(a.url, a.timeout)
        with lock:
            rows.append(r)

    end = time.time() + a.duration
    interval = 1.0 / a.rate
    nxt = time.time()
    while time.time() < end:
        threading.Thread(target=worker, daemon=True).start()
        nxt += interval
        time.sleep(max(0, nxt - time.time()))
    time.sleep(a.timeout + 1)

    rows.sort()
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ts", "status", "instance", "latency_s", "error"])
        for r in rows:
            w.writerow([f"{r[0]:.3f}", r[1], r[2], f"{r[3]:.4f}", r[4]])
    ok = sum(1 for r in rows if r[1] == 200)
    print(f"total={len(rows)} ok={ok} fail={len(rows) - ok}")


if __name__ == "__main__":
    main()
