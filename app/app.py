#!/usr/bin/env python3
"""CaribeShop demo app.

Servidor HTTP con solo la biblioteca estandar de Python (sin pip), para que la
instancia no necesite salir a Internet. Endpoints:

  /            pagina principal (hostname, zona, instancia)
  /health      sonda del balanceador: 200 si sana, 503 si existe FLAG_FILE
  /secret      lee el secreto de Key Vault con la identidad administrada y
               devuelve SOLO una huella (longitud + SHA-256 truncado)
  /work        carga de CPU controlada (para las pruebas de Locust)
  /egress-check  intenta salir a un sitio fijo de Internet (prueba P3.2)
"""
import hashlib
import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONFIG_FILE = os.getenv("CARIBESHOP_CONFIG", "/etc/caribeshop/config.json")
FLAG_FILE = os.getenv("CARIBESHOP_FLAG", "/var/lib/caribeshop/unhealthy")
IMDS = "http://169.254.169.254/metadata"
EGRESS_TARGET = "https://www.example.com"  # destino fijo: no es un proxy abierto

with open(CONFIG_FILE, encoding="utf-8") as fh:
    CONFIG = json.load(fh)

HOSTNAME = socket.gethostname()
_cache = {"meta": None, "secret": None, "secret_ts": 0.0}
_lock = threading.Lock()


def imds_get(path, params):
    url = f"{IMDS}/{path}?{params}"
    req = urllib.request.Request(url, headers={"Metadata": "true"})
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read().decode())


def instance_meta():
    if _cache["meta"] is None:
        try:
            data = imds_get("instance/compute", "api-version=2021-02-01")
            _cache["meta"] = {
                "name": data.get("name"),
                "zone": data.get("zone") or "n/a",
                "vmSize": data.get("vmSize"),
                "location": data.get("location"),
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"imds: {exc.__class__.__name__}"}
    return _cache["meta"]


def read_secret():
    """Token por IMDS (identidad administrada) -> GET al Key Vault."""
    with _lock:
        now = time.time()
        if _cache["secret"] and now - _cache["secret_ts"] < CONFIG.get("secret_cache_seconds", 60):
            return _cache["secret"], True
        tok = imds_get(
            "identity/oauth2/token",
            "api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net",
        )["access_token"]
        url = f"https://{CONFIG['vault_name']}.vault.azure.net/secrets/{CONFIG['secret_name']}?api-version=7.4"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            value = json.loads(resp.read().decode())["value"]
        _cache["secret"], _cache["secret_ts"] = value, now
        return value, False


def burn_cpu(ms):
    end = time.perf_counter() + ms / 1000.0
    x = 0
    while time.perf_counter() < end:
        x += sum(i * i for i in range(500))
    return x


class Handler(BaseHTTPRequestHandler):
    server_version = "CaribeShop/1.0"

    def log_message(self, fmt, *args):  # sin logs por peticion (rendimiento)
        return

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Instance", HOSTNAME)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/health":
            if os.path.exists(FLAG_FILE):
                return self._json(503, {"status": "unhealthy", "host": HOSTNAME})
            return self._json(200, {"status": "ok", "host": HOSTNAME})

        if path == "/":
            meta = instance_meta()
            html = (
                "<!doctype html><html><head><meta charset='utf-8'><title>CaribeShop</title></head>"
                "<body style='font-family:sans-serif;margin:3em'>"
                "<h1>CaribeShop &#127965;</h1><p>Temporada alta 2026</p>"
                f"<p>Instancia: <b>{HOSTNAME}</b> &middot; Zona: <b>{meta.get('zone')}</b> "
                f"&middot; Tamano: {meta.get('vmSize')}</p>"
                "<p>Endpoints: /health &middot; /secret &middot; /work &middot; /egress-check</p>"
                "</body></html>"
            )
            return self._send(200, html, "text/html; charset=utf-8")

        if path == "/secret":
            try:
                value, cached = read_secret()
            except urllib.error.HTTPError as exc:
                return self._json(502, {"keyvault": "error", "http_status": exc.code, "host": HOSTNAME})
            except Exception as exc:  # noqa: BLE001
                return self._json(502, {"keyvault": "error", "type": exc.__class__.__name__, "host": HOSTNAME})
            return self._json(200, {
                "keyvault": CONFIG["vault_name"],
                "secret_name": CONFIG["secret_name"],
                "length": len(value),
                "sha256_prefix": hashlib.sha256(value.encode()).hexdigest()[:12],
                "cached": cached,
                "host": HOSTNAME,
            })

        if path == "/work":
            burn_cpu(CONFIG.get("work_ms", 40))
            return self._json(200, {"ok": True, "host": HOSTNAME, "zone": instance_meta().get("zone")})

        if path == "/egress-check":
            t0 = time.time()
            try:
                urllib.request.urlopen(EGRESS_TARGET, timeout=5).close()
                result = "reachable"
            except Exception as exc:  # noqa: BLE001
                result = f"blocked ({exc.__class__.__name__})"
            return self._json(200, {"target": EGRESS_TARGET, "result": result,
                                    "elapsed_s": round(time.time() - t0, 2), "host": HOSTNAME})

        return self._json(404, {"error": "not found"})


class ReusePortServer(ThreadingHTTPServer):
    """Varios procesos escuchan el mismo puerto (SO_REUSEPORT): el kernel reparte
    las conexiones y se aprovechan todos los vCPU pese al GIL de Python."""
    daemon_threads = True
    request_queue_size = 256

    def server_bind(self):
        if hasattr(socket, "SO_REUSEPORT"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        super().server_bind()


if __name__ == "__main__":
    workers = int(os.getenv("WORKERS", str(os.cpu_count() or 1)))
    if hasattr(os, "fork"):
        for _ in range(workers - 1):
            if os.fork() == 0:  # hijo: deja de crear procesos y sirve
                break
    srv = ReusePortServer(("0.0.0.0", int(os.getenv("PORT", "80"))), Handler)
    srv.serve_forever()
