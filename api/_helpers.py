"""
Trading Different Bot — Shared helpers for Vercel serverless functions.
All state is persisted in Vercel KV (Upstash Redis REST API).

KV keys:
  td:pools        — JSON: {"scalping": {...}, "swing": {...}}
  td:mode         — string: "scalping" | "swing"
  td:trendiff     — string: "bullish" | "bearish"
  td:chat_id      — string: Telegram chat ID
  td:alerts_sent  — JSON list: [alert_key, ...]
  td:trade:{id}   — JSON: trade session state
  td:trades_log   — JSON list: trade records
"""

import os, json, requests
import pytz
from datetime import datetime

# ── Credentials ──────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8538242111:AAGPdp2z9BkcDmUGtpnBdgscyLvYSD_dxT0")
KV_URL   = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

# ── Timezones ─────────────────────────────────────────────────
ET   = pytz.timezone("America/New_York")
BSAS = pytz.timezone("America/Argentina/Buenos_Aires")

# ── Macro calendar ───────────────────────────────────────────
MACRO_EVENTS = [
    {"name": "FOMC Decisión",  "dt": "2026-04-29 14:00", "impact": "EXTREMO",  "no_trade_min": 60},
    {"name": "NFP / Payrolls", "dt": "2026-05-01 08:30", "impact": "MUY ALTO", "no_trade_min": 15},
    {"name": "CPI Inflación",  "dt": "2026-05-13 08:30", "impact": "MUY ALTO", "no_trade_min": 30},
    {"name": "FOMC Reunión",   "dt": "2026-06-17 14:00", "impact": "EXTREMO",  "no_trade_min": 60},
    {"name": "NFP / Payrolls", "dt": "2026-06-05 08:30", "impact": "MUY ALTO", "no_trade_min": 15},
    {"name": "CPI Inflación",  "dt": "2026-06-10 08:30", "impact": "MUY ALTO", "no_trade_min": 30},
    {"name": "FOMC Reunión",   "dt": "2026-07-29 14:00", "impact": "EXTREMO",  "no_trade_min": 60},
]

# ── Default pools (fallback when KV is empty) ─────────────────
DEFAULT_POOLS = {
    "scalping": {
        "long_pools": [
            {"low": 74500, "high": 76000, "intensity": "red",    "label": "Pool LARGO Principal"},
            {"low": 73000, "high": 73800, "intensity": "yellow", "label": "Pool LARGO Secundario"},
        ],
        "short_pools": [
            {"low": 77250, "high": 78350, "intensity": "orange", "label": "Pool CORTO Inmediato"},
            {"low": 80000, "high": 81360, "intensity": "yellow", "label": "Pool CORTO $80K"},
        ],
    },
    "swing": {
        "long_pools": [
            {"low": 74500, "high": 76000, "intensity": "red",    "label": "Pool LARGO Macro"},
            {"low": 70000, "high": 73000, "intensity": "yellow", "label": "Pool LARGO $70K-$73K"},
            {"low": 59050, "high": 62935, "intensity": "green",  "label": "Pool LARGO Profundo"},
        ],
        "short_pools": [
            {"low": 77250,  "high": 78350,  "intensity": "orange", "label": "Pool CORTO Inmediato"},
            {"low": 80000,  "high": 81360,  "intensity": "yellow", "label": "Pool CORTO $80K"},
            {"low": 100000, "high": 110000, "intensity": "orange", "label": "Pool CORTO $100K-$110K"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────
# KV (Upstash Redis REST API)
# ─────────────────────────────────────────────────────────────
def _kv_headers():
    return {"Authorization": f"Bearer {KV_TOKEN}"}

def kv_get(key):
    if not KV_URL or not KV_TOKEN:
        return None
    try:
        r = requests.get(f"{KV_URL}/get/{key}", headers=_kv_headers(), timeout=5)
        result = r.json().get("result")
        if result is None:
            return None
        return json.loads(result)
    except Exception as e:
        print(f"[KV] kv_get({key}) error: {e}")
        return None

def kv_set(key, value, ex=None):
    if not KV_URL or not KV_TOKEN:
        return False
    try:
        url = f"{KV_URL}/set/{key}"
        if ex:
            url += f"?ex={ex}"
        r = requests.post(url, headers=_kv_headers(), data=json.dumps(value), timeout=5)
        return r.ok
    except Exception as e:
        print(f"[KV] kv_set({key}) error: {e}")
        return False

def kv_delete(key):
    if not KV_URL or not KV_TOKEN:
        return False
    try:
        r = requests.get(f"{KV_URL}/del/{key}", headers=_kv_headers(), timeout=5)
        return r.ok
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────
def get_state():
    return {
        "mode":     kv_get("td:mode")     or "scalping",
        "trendiff": kv_get("td:trendiff") or "bearish",
        "chat_id":  kv_get("td:chat_id"),
    }

def get_pools():
    pools = kv_get("td:pools")
    if pools:
        # Flatten TF-structured pools to flat format
        result = {}
        for mode in ("scalping", "swing"):
            if mode in pools:
                result[mode] = _flatten_pools(pools[mode])
        return result if result else DEFAULT_POOLS
    return DEFAULT_POOLS

def get_alerts_sent():
    alerts = kv_get("td:alerts_sent")
    return set(alerts) if alerts else set()

def save_alerts_sent(alerts_set):
    # Keep only last 200 to avoid unbounded growth
    lst = list(alerts_set)[-200:]
    kv_set("td:alerts_sent", lst)

def reset_alerts():
    kv_set("td:alerts_sent", [])

# ─────────────────────────────────────────────────────────────
# Pool helpers
# ─────────────────────────────────────────────────────────────
def _flatten_pools(mode_data):
    """Flatten TF-keyed pools {'1H': {...}, '4H': {...}} → {'long_pools': [...], 'short_pools': [...]}"""
    if "long_pools" in mode_data or "short_pools" in mode_data:
        return mode_data  # already flat

    merged_long, merged_short = [], []
    seen_long, seen_short = set(), set()

    for tf, tf_data in mode_data.items():
        if not isinstance(tf_data, dict):
            continue
        for pool in tf_data.get("long_pools", []):
            key = (pool.get("low"), pool.get("high"))
            if key not in seen_long:
                seen_long.add(key)
                merged_long.append(pool)
        for pool in tf_data.get("short_pools", []):
            key = (pool.get("low"), pool.get("high"))
            if key not in seen_short:
                seen_short.add(key)
                merged_short.append(pool)

    merged_long.sort(key=lambda p: p.get("low", 0))
    merged_short.sort(key=lambda p: p.get("low", 0))
    return {"long_pools": merged_long, "short_pools": merged_short}

# ─────────────────────────────────────────────────────────────
# BTC Price
# ─────────────────────────────────────────────────────────────
def get_btc_price():
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": "BTCUSDT"},
            timeout=6,
        )
        d = r.json()
        return float(d["lastPrice"]), float(d["priceChangePercent"])
    except Exception as e:
        print(f"[ERROR] Binance: {e}")
        return None, None

def fmt_price(p):
    return f"${p:,.0f}"

# ─────────────────────────────────────────────────────────────
# Macro calendar
# ─────────────────────────────────────────────────────────────
def check_no_trade():
    now_et = datetime.now(ET)
    for ev in MACRO_EVENTS:
        ev_dt = ET.localize(datetime.strptime(ev["dt"], "%Y-%m-%d %H:%M"))
        diff_min = (ev_dt - now_et).total_seconds() / 60
        window = ev["no_trade_min"]
        if -30 <= diff_min <= window:
            return True, f"⚠️ NO-TRADE ZONE\n{ev['name']} — {ev['impact']}\nHorario: {ev['dt']} ET"
    return False, ""

def get_upcoming_events(hours=48):
    now_et = datetime.now(ET)
    upcoming = []
    for ev in MACRO_EVENTS:
        ev_dt = ET.localize(datetime.strptime(ev["dt"], "%Y-%m-%d %H:%M"))
        diff_h = (ev_dt - now_et).total_seconds() / 3600
        if 0 < diff_h <= hours:
            upcoming.append((ev, diff_h))
    return upcoming

# ─────────────────────────────────────────────────────────────
# Signal evaluation
# ─────────────────────────────────────────────────────────────
def find_nearest_pool(price, pools, side):
    pool_list = pools.get(f"{side}_pools", [])
    best, dist = None, float("inf")
    for p in pool_list:
        center = (p["low"] + p["high"]) / 2
        d = abs(price - center)
        if d < dist:
            dist = d
            best = p
    return best

def is_in_pool(price, pool, tolerance=0.0):
    return pool["low"] * (1 - tolerance) <= price <= pool["high"] * (1 + tolerance)

def evaluate_signal(price, pools_for_mode, trendiff):
    """Evaluates the current signal for a given price, mode pools, and trendiff."""
    no_trade, no_msg = check_no_trade()
    if no_trade:
        return {"type": "NOTRADE", "text": no_msg, "entry": None, "sl": None, "tp": None, "pool": None}

    valid_intensities = {"red", "orange", "yellow"}

    # LONG pool check
    for pool in pools_for_mode.get("long_pools", []):
        if pool["intensity"] not in valid_intensities:
            continue
        if is_in_pool(price, pool, tolerance=0.003):
            if trendiff == "bullish" or pool["intensity"] == "red":
                sl  = pool["low"] * 0.998
                ns  = find_nearest_pool(price, pools_for_mode, "short")
                tp  = ns["low"] if ns else price * 1.025
                rr  = round((tp - price) / (price - sl), 1) if price > sl else 0
                return {
                    "type": "LONG", "pool": pool, "entry": price, "sl": sl, "tp": tp,
                    "tp_label": ns["label"] if ns else "Pool corto siguiente", "rr": rr,
                }

    # SHORT pool check
    for pool in pools_for_mode.get("short_pools", []):
        if pool["intensity"] not in valid_intensities:
            continue
        if is_in_pool(price, pool, tolerance=0.003):
            if trendiff == "bearish" or pool["intensity"] == "red":
                sl  = pool["high"] * 1.002
                nl  = find_nearest_pool(price, pools_for_mode, "long")
                tp  = nl["high"] if nl else price * 0.975
                rr  = round((price - tp) / (sl - price), 1) if sl > price else 0
                return {
                    "type": "SHORT", "pool": pool, "entry": price, "sl": sl, "tp": tp,
                    "tp_label": nl["label"] if nl else "Pool largo siguiente", "rr": rr,
                }

    # Graduated proximity alerts (3 levels: FAR 2%, NEAR 1%, HOT 0.3%)
    for pool in pools_for_mode.get("long_pools", []):
        if pool["intensity"] not in valid_intensities:
            continue
        low, high = pool["low"], pool["high"]
        if price < low:
            dist_pct = (low - price) / price * 100
            if 0 < dist_pct <= 2.0:
                level = "HOT" if dist_pct <= 0.3 else "NEAR" if dist_pct <= 1.0 else "FAR"
                return {"type": "APPROACHING_LONG", "pool": pool, "dist_pct": dist_pct, "level": level}

    for pool in pools_for_mode.get("short_pools", []):
        if pool["intensity"] not in valid_intensities:
            continue
        low, high = pool["low"], pool["high"]
        if price > high:
            dist_pct = (price - high) / price * 100
            if 0 < dist_pct <= 2.0:
                level = "HOT" if dist_pct <= 0.3 else "NEAR" if dist_pct <= 1.0 else "FAR"
                return {"type": "APPROACHING_SHORT", "pool": pool, "dist_pct": dist_pct, "level": level}

    return {"type": "NEUTRAL", "pool": None}

# ─────────────────────────────────────────────────────────────
# Message builders
# ─────────────────────────────────────────────────────────────
def build_signal_message(price, change, sig, mode, trendiff):
    mode_emoji     = "⚡" if mode == "scalping" else "📈"
    trendiff_emoji = "🟢" if trendiff == "bullish" else "🔴"
    sig_type       = sig.get("type", "NEUTRAL")

    if sig_type == "LONG":
        header = "🟢 *SEÑAL DE COMPRA — LONG*"
        body = (
            f"*Pool:* {sig['pool']['label']}\n"
            f"*Intensidad:* {sig['pool']['intensity'].upper()}\n\n"
            f"💰 *Entrada:* {fmt_price(sig['entry'])}\n"
            f"🛡️ *Stop Loss:* {fmt_price(sig['sl'])}\n"
            f"🎯 *Take Profit:* {fmt_price(sig['tp'])} → {sig.get('tp_label','')}\n"
            f"⚖️ *Ratio R/R:* {sig['rr']}:1\n"
        )
    elif sig_type == "SHORT":
        header = "🔴 *SEÑAL DE VENTA — SHORT*"
        body = (
            f"*Pool:* {sig['pool']['label']}\n"
            f"*Intensidad:* {sig['pool']['intensity'].upper()}\n\n"
            f"💰 *Entrada:* {fmt_price(sig['entry'])}\n"
            f"🛡️ *Stop Loss:* {fmt_price(sig['sl'])}\n"
            f"🎯 *Take Profit:* {fmt_price(sig['tp'])} → {sig.get('tp_label','')}\n"
            f"⚖️ *Ratio R/R:* {sig['rr']}:1\n"
        )
    elif sig_type == "NOTRADE":
        header = "🚫 *NO-TRADE ZONE ACTIVA*"
        body   = sig["text"] + "\n"
    elif sig_type in ("APPROACHING_LONG", "APPROACHING_SHORT"):
        level   = sig.get("level", "FAR")
        icons   = {"HOT": "🔥", "NEAR": "⚡", "FAR": "📡"}
        urgency = {"HOT": "ENTRADA INMINENTE", "NEAR": "ATENCIÓN: entrada próxima", "FAR": "Acercándose"}
        side    = "LARGO" if sig_type == "APPROACHING_LONG" else "CORTO"
        header  = f"{icons.get(level,'⚡')} *{urgency.get(level,'Acercándose')} — Pool {side}*"
        body    = (
            f"Pool: *{sig['pool']['label']}*\n"
            f"Intensidad: {sig['pool']['intensity'].upper()}\n"
            f"Distancia: *{sig['dist_pct']:.2f}%* del pool\n"
        )
        if level == "HOT":
            body += "⏰ Precio a punto de tocar zona — preparar orden\n"
    else:
        return None  # NEUTRAL — don't send

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{body}"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{mode_emoji} Modo: *{mode.upper()}*\n"
        f"{trendiff_emoji} TrenDiff: *{trendiff.upper()}*\n"
        f"💵 BTC: *{fmt_price(price)}* ({change:+.2f}%)\n"
        f"🕐 {datetime.now(ET).strftime('%d/%m %H:%M ET')}\n"
        f"📊 [Dashboard TD](https://trading-different.vercel.app)"
    )

# ─────────────────────────────────────────────────────────────
# Telegram API
# ─────────────────────────────────────────────────────────────
def send_telegram(chat_id, text, parse_mode="Markdown", reply_markup=None):
    if not chat_id:
        print("[WARN] send_telegram called without chat_id")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"[WARN] Telegram send error: {r.text}")
        return r.ok
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")
        return False

def answer_callback(callback_id):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=5,
        )
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# Command handlers
# ─────────────────────────────────────────────────────────────
def handle_cmd_precio(chat_id, state, pools):
    price, change = get_btc_price()
    if not price:
        send_telegram(chat_id, "❌ Error al obtener precio de Binance.")
        return
    mode_pools = pools.get(state["mode"], pools.get("scalping", {}))
    sig = evaluate_signal(price, mode_pools, state["trendiff"])
    type_map = {
        "LONG": "🟢 LONG — Señal activa",
        "SHORT": "🔴 SHORT — Señal activa",
        "NOTRADE": "🚫 NO-TRADE ZONE",
        "APPROACHING_LONG": "⚡ Acercándose a pool LARGO",
        "APPROACHING_SHORT": "⚡ Acercándose a pool CORTO",
        "NEUTRAL": "⏳ Zona neutral — Esperando pool",
    }
    send_telegram(
        chat_id,
        f"💵 *BTC/USDT* → *{fmt_price(price)}* ({change:+.2f}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Señal: {type_map.get(sig['type'], '—')}\n"
        f"⚡ Modo: {state['mode'].upper()}\n"
        f"🎯 TrenDiff: {state['trendiff'].upper()}\n"
        f"🕐 {datetime.now(ET).strftime('%d/%m/%Y %H:%M ET')}",
    )

def handle_cmd_pools(chat_id, state, pools):
    mode_pools = pools.get(state["mode"], pools.get("scalping", {}))
    ie = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢"}
    msg = f"📋 *Pools Activos — Modo {state['mode'].upper()}*\n━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "\n*⬆️ CORTOS (resistencias/objetivos):*\n"
    for p in reversed(mode_pools.get("short_pools", [])):
        msg += f"{ie.get(p['intensity'],'⚪')} {p['label']}: {fmt_price(p['low'])}—{fmt_price(p['high'])}\n"
    msg += "\n*⬇️ LARGOS (soportes/entradas):*\n"
    for p in mode_pools.get("long_pools", []):
        msg += f"{ie.get(p['intensity'],'⚪')} {p['label']}: {fmt_price(p['low'])}—{fmt_price(p['high'])}\n"
    send_telegram(chat_id, msg)

def handle_cmd_estado(chat_id, state, pools):
    price, change = get_btc_price()
    upcoming  = get_upcoming_events(72)
    no_trade, nt_msg = check_no_trade()
    msg = (
        f"📊 *ESTADO COMPLETO DEL MERCADO*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 BTC: *{fmt_price(price) if price else '---'}* ({change:+.2f}% 24h)\n"
        f"🎯 TrenDiff: *{state['trendiff'].upper()}*\n"
        f"⚡ Modo: *{state['mode'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if no_trade:
        msg += f"🚫 *{nt_msg}*\n━━━━━━━━━━━━━━━━━━━━━\n"
    if upcoming:
        msg += "📅 *Próximos eventos macro:*\n"
        for ev, hours in upcoming[:3]:
            msg += f"• {ev['name']} — en {hours:.0f}h ({ev['impact']})\n"
    else:
        msg += "📅 Sin eventos macro en 72h\n"
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ Scalping", "callback_data": "mode_scalping"},
             {"text": "📈 Swing",    "callback_data": "mode_swing"}],
            [{"text": "🟢 Bullish",  "callback_data": "td_bullish"},
             {"text": "🔴 Bearish",  "callback_data": "td_bearish"}],
            [{"text": "📋 Ver Pools", "callback_data": "cmd_pools"},
             {"text": "💰 Precio",   "callback_data": "cmd_precio"}],
        ]
    }
    send_telegram(chat_id, msg, reply_markup=keyboard)

def handle_cmd_ayuda(chat_id):
    send_telegram(
        chat_id,
        "🤖 *Trading Different Bot — Comandos:*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "/precio — Precio actual + señal\n"
        "/pools — Pools activos del modo actual\n"
        "/estado — Resumen completo del mercado\n"
        "/scalping — Cambiar a modo Scalping\n"
        "/swing — Cambiar a modo Swing\n"
        "/bullish — TrenDiff ALCISTA\n"
        "/bearish — TrenDiff BAJISTA\n"
        "/trade — Registrar un trade\n"
        "/ayuda — Esta ayuda\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 [Dashboard](https://trading-different.vercel.app)",
    )

def handle_cmd_trade(chat_id, price=None):
    price_str = ""
    if not price:
        price, _ = get_btc_price()
    if price:
        price_str = f"*Precio actual: {fmt_price(price)}*\n"
    # Save trade session to KV
    session = {"step": "awaiting_direction", "data": {}}
    kv_set(f"td:trade:{chat_id}", session, ex=600)  # expire in 10 min
    send_telegram(
        chat_id,
        f"📝 *Registrar nuevo trade*\n"
        f"{'━'*20}\n"
        f"{price_str}"
        f"¿Dirección? Respondé *LONG* o *SHORT*\n"
        f"_(Escribí /cancelar para salir)_",
    )

def handle_trade_flow(chat_id, user_text):
    """Stateful trade registration via KV-stored session."""
    sess = kv_get(f"td:trade:{chat_id}")
    if not sess:
        return False  # no active session

    if user_text.lower() in ["/cancelar", "cancelar", "cancel"]:
        kv_delete(f"td:trade:{chat_id}")
        send_telegram(chat_id, "❌ Registro de trade cancelado.")
        return True

    step = sess.get("step")
    data = sess.get("data", {})

    if step == "awaiting_direction":
        t = user_text.upper()
        if t in ["LONG", "L", "▲"]:
            data["direction"] = "LONG"
        elif t in ["SHORT", "S", "▼"]:
            data["direction"] = "SHORT"
        else:
            send_telegram(chat_id, "⚠️ Escribí *LONG* o *SHORT*")
            return True
        sess = {"step": "awaiting_entry", "data": data}
        kv_set(f"td:trade:{chat_id}", sess, ex=600)
        send_telegram(chat_id, "💵 ¿Precio de *ENTRADA*? (o /cancelar)")
        return True

    if step == "awaiting_entry":
        try:
            data["entry"] = float(user_text.replace(",", "").replace("$", ""))
            sess = {"step": "awaiting_sl", "data": data}
            kv_set(f"td:trade:{chat_id}", sess, ex=600)
            send_telegram(chat_id, "🛑 ¿Stop Loss? (precio o /cancelar)")
        except Exception:
            send_telegram(chat_id, "⚠️ Ingresá un precio válido. Ej: 95000")
        return True

    if step == "awaiting_sl":
        try:
            data["sl"] = float(user_text.replace(",", "").replace("$", ""))
            sess = {"step": "awaiting_tp", "data": data}
            kv_set(f"td:trade:{chat_id}", sess, ex=600)
            send_telegram(chat_id, "🎯 ¿Take Profit? (precio o /cancelar)")
        except Exception:
            send_telegram(chat_id, "⚠️ Ingresá un precio válido.")
        return True

    if step == "awaiting_tp":
        try:
            data["tp"] = float(user_text.replace(",", "").replace("$", ""))
            sess = {"step": "awaiting_pool", "data": data}
            kv_set(f"td:trade:{chat_id}", sess, ex=600)
            send_telegram(chat_id, "🏷 ¿Nombre del pool? (o escribí 'n/a')")
        except Exception:
            send_telegram(chat_id, "⚠️ Ingresá un precio válido.")
        return True

    if step == "awaiting_pool":
        data["pool"] = user_text if user_text.lower() != "n/a" else "Manual"
        e, sl, tp = data["entry"], data["sl"], data["tp"]
        if data["direction"] == "LONG":
            rr = round((tp - e) / (e - sl), 2) if e > sl else 0
        else:
            rr = round((e - tp) / (sl - e), 2) if sl > e else 0
        data["rr"] = rr
        data["ts"] = datetime.now(BSAS).isoformat()
        trade_entry = {
            "ts": data["ts"], "dir": data["direction"], "pool": data["pool"],
            "entry": e, "sl": sl, "tp": tp, "rr": rr, "result": "OPEN", "exit": None,
            "notes": "Registrado via bot Vercel",
        }
        # Append to trades log in KV
        trades = kv_get("td:trades_log") or []
        trades.append(trade_entry)
        kv_set("td:trades_log", trades)
        kv_delete(f"td:trade:{chat_id}")
        direction_emoji = "🟢▲" if data["direction"] == "LONG" else "🔴▼"
        send_telegram(
            chat_id,
            f"✅ *Trade registrado!*\n"
            f"{'━'*20}\n"
            f"{direction_emoji} *{data['direction']}* — {data['pool']}\n"
            f"💵 Entrada: *${e:,.0f}*\n"
            f"🛑 SL: *${sl:,.0f}*\n"
            f"🎯 TP: *${tp:,.0f}*\n"
            f"📐 R:R = *{rr:.1f}:1*\n"
            f"{'━'*20}\n"
            f"💾 Guardado en KV Cloud",
        )
        return True

    return False

# ─────────────────────────────────────────────────────────────
# Daily briefing builder
# ─────────────────────────────────────────────────────────────
def build_daily_briefing(price, change, state, pools):
    mode_pools   = pools.get(state["mode"], pools.get("scalping", {}))
    mode_emoji   = "⚡" if state["mode"] == "scalping" else "📈"
    td_emoji     = "🟢" if state["trendiff"] == "bullish" else "🔴"
    ie           = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢"}
    upcoming     = get_upcoming_events(24)

    nearest_long  = (min(mode_pools.get("long_pools", []),
                        key=lambda p: abs(price - (p["low"]+p["high"])/2))
                     if mode_pools.get("long_pools") and price else None)
    nearest_short = (min(mode_pools.get("short_pools", []),
                        key=lambda p: abs(price - (p["low"]+p["high"])/2))
                     if mode_pools.get("short_pools") and price else None)

    long_str  = (f"{ie.get(nearest_long['intensity'],'⚪')} {nearest_long['label']}: "
                 f"{fmt_price(nearest_long['low'])}–{fmt_price(nearest_long['high'])}"
                 if nearest_long else "—")
    short_str = (f"{ie.get(nearest_short['intensity'],'⚪')} {nearest_short['label']}: "
                 f"{fmt_price(nearest_short['low'])}–{fmt_price(nearest_short['high'])}"
                 if nearest_short else "—")

    macro_str = "✅ Sin eventos de alto impacto en 24h"
    if upcoming:
        macro_str = "⚠️ *Eventos hoy:*\n" + "\n".join(
            [f"• {ev['name']} ({ev['impact']}) — {ev['dt'][11:16]} ET" for ev, h in upcoming[:3]]
        )

    # Trade stats
    trade_summary = ""
    trades = kv_get("td:trades_log") or []
    recent = [t for t in trades if t.get("result") in ("WIN", "LOSS")]
    if recent:
        wins = sum(1 for t in recent if t["result"] == "WIN")
        wr   = round(wins / len(recent) * 100)
        trade_summary = f"\n📊 *Trades cerrados:* {len(recent)} ({wr}% winrate)"

    return (
        f"☀️ *Buenos días! Briefing Trading Different*\n"
        f"🕗 {datetime.now(BSAS).strftime('%d/%m/%Y %H:%M')} BsAs\n"
        f"{'━'*22}\n"
        f"💵 BTC: *{fmt_price(price) if price else '---'}* ({change:+.2f}% 24h)\n"
        f"{mode_emoji} Modo: *{state['mode'].upper()}*\n"
        f"{td_emoji} TrenDiff: *{state['trendiff'].upper()}*\n"
        f"{'━'*22}\n"
        f"*Pools más cercanos:*\n"
        f"⬆️ Short: {short_str}\n"
        f"⬇️ Long:  {long_str}\n"
        f"{'━'*22}\n"
        f"{macro_str}{trade_summary}\n"
        f"{'━'*22}\n"
        f"💪 Que sea un buen día de trading!\n"
        f"_Usa /precio para señal en tiempo real_"
    )
