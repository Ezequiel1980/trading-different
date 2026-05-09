"""
GET /api/cron/check
Price proximity monitor — runs every 5 minutes via Vercel Cron.
Checks BTC price against active pools and sends Telegram alerts.
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os

# _helpers.py is one level up (api/_helpers.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _helpers import (
    get_btc_price, fmt_price, get_state, get_pools,
    get_alerts_sent, save_alerts_sent,
    evaluate_signal, build_signal_message,
    send_telegram,
)


def run_check():
    state = get_state()
    chat_id = state.get("chat_id")
    if not chat_id:
        print("[CRON/check] No chat_id configured — skipping")
        return {"skipped": True, "reason": "no_chat_id"}

    price, change = get_btc_price()
    if not price:
        print("[CRON/check] Could not fetch BTC price")
        return {"skipped": True, "reason": "no_price"}

    pools      = get_pools()
    mode_pools = pools.get(state["mode"], pools.get("scalping", {}))
    sig        = evaluate_signal(price, mode_pools, state["trendiff"])
    sig_type   = sig.get("type", "NEUTRAL")

    alert_types = {"LONG", "SHORT", "NOTRADE", "APPROACHING_LONG", "APPROACHING_SHORT"}

    if sig_type not in alert_types:
        print(f"[CRON/check] BTC={fmt_price(price)} | {sig_type} — no alert")
        return {"price": price, "signal": sig_type, "alerted": False}

    # Build dedup key
    pool  = sig.get("pool")
    level = sig.get("level", "")
    key   = f"{sig_type}_{pool['label'] if pool else 'macro'}_{level}_{round(price / 1000)}"

    alerts_sent = get_alerts_sent()
    if key in alerts_sent:
        print(f"[CRON/check] BTC={fmt_price(price)} | {sig_type} — already alerted ({key})")
        return {"price": price, "signal": sig_type, "alerted": False, "reason": "dedup"}

    # Send alert
    msg = build_signal_message(price, change, sig, state["mode"], state["trendiff"])
    if msg:
        sent = send_telegram(chat_id, msg)
        if sent:
            alerts_sent.add(key)
            # Prune to avoid unbounded growth
            if len(alerts_sent) > 150:
                # Keep only recent 100 entries
                alerts_sent = set(list(alerts_sent)[-100:])
            save_alerts_sent(alerts_sent)
            print(f"[CRON/check] ✅ ALERTA ENVIADA: {sig_type} @ {fmt_price(price)}")
            return {"price": price, "signal": sig_type, "alerted": True}

    return {"price": price, "signal": sig_type, "alerted": False}


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            result = run_check()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            print(f"[ERROR] cron/check: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
