"""
POST /api/webhook
Telegram webhook handler — processes all bot commands and messages.
Register this URL with Telegram:
  https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://trading-different.vercel.app/api/webhook
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import (
    kv_get, kv_set, get_state, get_pools,
    send_telegram, answer_callback,
    handle_cmd_precio, handle_cmd_pools, handle_cmd_estado,
    handle_cmd_ayuda, handle_cmd_trade, handle_trade_flow,
    get_btc_price, fmt_price,
)


def process_update(upd):
    """Route a single Telegram update to the correct handler."""
    # ── Inline keyboard callbacks ──────────────────────────────
    cb = upd.get("callback_query")
    if cb:
        answer_callback(cb["id"])
        chat_id = str(cb["from"]["id"])
        state   = get_state()
        pools   = get_pools()
        data_cb = cb.get("data", "")
        if data_cb == "mode_scalping":
            kv_set("td:mode", "scalping")
            send_telegram(chat_id, "✅ Modo *SCALPING* ⚡")
        elif data_cb == "mode_swing":
            kv_set("td:mode", "swing")
            send_telegram(chat_id, "✅ Modo *SWING* 📈")
        elif data_cb == "td_bullish":
            kv_set("td:trendiff", "bullish")
            send_telegram(chat_id, "🟢 TrenDiff → *BULLISH*\nSolo se buscarán entradas LARGAS.")
        elif data_cb == "td_bearish":
            kv_set("td:trendiff", "bearish")
            send_telegram(chat_id, "🔴 TrenDiff → *BEARISH*\nSolo se buscarán entradas CORTAS.")
        elif data_cb == "cmd_pools":
            handle_cmd_pools(chat_id, state, pools)
        elif data_cb == "cmd_precio":
            handle_cmd_precio(chat_id, state, pools)
        return

    # ── Regular messages ───────────────────────────────────────
    msg  = upd.get("message", {})
    if not msg:
        return

    chat    = msg.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text    = msg.get("text", "").strip()

    if not chat_id or not text:
        return

    # ── Auto-detect chat ID on first message ──────────────────
    saved_chat = kv_get("td:chat_id")
    if not saved_chat:
        kv_set("td:chat_id", chat_id)
        nombre = chat.get("first_name", "Trader")
        send_telegram(
            chat_id,
            f"👋 *Hola {nombre}!*\n"
            f"✅ Chat ID detectado: `{chat_id}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *@DataDifferentbot* listo para operar\n"
            f"Escribí /ayuda para ver los comandos.",
        )
        print(f"[OK] Primer usuario registrado: {nombre} (ID: {chat_id})")
        # Don't return — still process the command below

    # ── Authorize only known chat ID ──────────────────────────
    authorized = kv_get("td:chat_id")
    if authorized and chat_id != str(authorized):
        send_telegram(chat_id, "⛔ No autorizado.")
        return

    # ── Trade conversation flow (stateful via KV) ─────────────
    if handle_trade_flow(chat_id, text):
        return

    # ── Commands ──────────────────────────────────────────────
    state = get_state()
    pools = get_pools()
    cmd   = text.lower().split()[0]  # first word (handle /cmd@botname format)
    cmd   = cmd.split("@")[0]        # strip @botname suffix

    if cmd in ("/precio", "/start"):
        handle_cmd_precio(chat_id, state, pools)
    elif cmd == "/pools":
        handle_cmd_pools(chat_id, state, pools)
    elif cmd == "/estado":
        handle_cmd_estado(chat_id, state, pools)
    elif cmd == "/trade":
        handle_cmd_trade(chat_id)
    elif cmd == "/ayuda":
        handle_cmd_ayuda(chat_id)
    elif cmd == "/scalping":
        kv_set("td:mode", "scalping")
        send_telegram(chat_id, "✅ Modo cambiado a *SCALPING* ⚡")
    elif cmd == "/swing":
        kv_set("td:mode", "swing")
        send_telegram(chat_id, "✅ Modo cambiado a *SWING* 📈")
    elif cmd == "/bullish":
        kv_set("td:trendiff", "bullish")
        send_telegram(chat_id, "🟢 TrenDiff → *BULLISH*\nSolo se buscarán entradas LARGAS.")
    elif cmd == "/bearish":
        kv_set("td:trendiff", "bearish")
        send_telegram(chat_id, "🔴 TrenDiff → *BEARISH*\nSolo se buscarán entradas CORTAS.")
    else:
        # Unknown text — not in a trade session, ignore silently
        pass


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            upd    = json.loads(body)
            process_update(upd)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            # Always return 200 to Telegram to prevent retries
            print(f"[ERROR] webhook: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":false}')

    def do_GET(self):
        # Health check
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"TD Webhook OK")
