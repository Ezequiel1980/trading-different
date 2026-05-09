"""
POST /api/alert
Custom alert endpoint — called by dashboard when a user-defined alert fires.
Sends the alert message to Telegram immediately.
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import kv_get, send_telegram, fmt_price


def _cors_headers(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        _cors_headers(self)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)

            chat_id = kv_get("td:chat_id")
            if chat_id:
                title = data.get("title", "🎯 Alerta personalizada")
                body_text = data.get("body", "")
                price = data.get("price", "")
                price_str = fmt_price(price) if price else "---"
                msg = f"{title}\n_{body_text}_\n💵 Precio: {price_str}"
                send_telegram(chat_id, msg)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            _cors_headers(self)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            _cors_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
