"""
POST /api/sync
Receives pool config from the dashboard and saves it to Vercel KV.
Called by exportPoolsConfig() in dashboard.html when the user saves pools.
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os

# Allow importing shared helpers from api/_helpers.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import kv_set, kv_get, _flatten_pools, reset_alerts


def _cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence access logs

    def do_OPTIONS(self):
        self.send_response(200)
        _cors_headers(self)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)

            changed = []

            # Save pools (flatten TF structure if needed)
            if "pools" in data:
                pools = data["pools"]
                for mode in ("scalping", "swing"):
                    if mode in pools:
                        pools[mode] = _flatten_pools(pools[mode])
                kv_set("td:pools", pools)
                changed.append("pools")
                # Reset alert cache so new pool config triggers fresh alerts
                reset_alerts()

            if "mode" in data and data["mode"] in ("scalping", "swing"):
                kv_set("td:mode", data["mode"])
                changed.append(f"mode={data['mode']}")

            if "trendiff" in data and data["trendiff"] in ("bullish", "bearish"):
                kv_set("td:trendiff", data["trendiff"])
                changed.append(f"trendiff={data['trendiff']}")

            ts = data.get("exported_at", "")
            print(f"[SYNC] Dashboard → KV: {', '.join(changed)}  [{ts}]")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            _cors_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "applied": changed}).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            _cors_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
