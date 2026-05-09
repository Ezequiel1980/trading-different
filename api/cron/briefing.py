"""
GET /api/cron/briefing
Daily morning briefing — runs at 11:00 UTC (= 8:00 AM Buenos Aires UTC-3)
via Vercel Cron. Sends a full market summary to Telegram.
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _helpers import (
    get_btc_price, get_state, get_pools,
    reset_alerts, send_telegram,
    build_daily_briefing,
)


def run_briefing():
    state   = get_state()
    chat_id = state.get("chat_id")
    if not chat_id:
        print("[CRON/briefing] No chat_id — skipping")
        return {"skipped": True, "reason": "no_chat_id"}

    price, change = get_btc_price()
    pools = get_pools()

    # Reset daily alert cache so the day starts fresh
    reset_alerts()

    msg  = build_daily_briefing(price, change, state, pools)
    sent = send_telegram(chat_id, msg)
    print(f"[CRON/briefing] Briefing enviado → chat {chat_id}")
    return {"ok": sent}


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            result = run_briefing()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            print(f"[ERROR] cron/briefing: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
