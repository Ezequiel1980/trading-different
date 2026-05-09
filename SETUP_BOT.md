# Setup — Trading Different BTC Bot

El bot ahora corre **100% en Vercel** (sin Python local ni localhost).
Los datos se persisten en **Vercel KV** (Redis cloud).

---

## 🚀 Despliegue en Vercel

### Paso 1 — Subir cambios a GitHub

```powershell
cd "C:\Users\Ezequiel\Documents\Claude\Projects\Trading Different"
git add -A
git commit -m "Bot Vercel: API serverless + cron jobs + KV"
git push
```

Vercel detecta el push y hace deploy automáticamente.

---

### Paso 2 — Crear Vercel KV Store

1. Ir a vercel.com → tu proyecto `trading-different`
2. Tab **Storage** → **Create Database** → elegir **KV (Upstash Redis)**
3. Darle un nombre (ej: `td-bot-kv`) → **Create & Connect**
4. Vercel inyecta automáticamente estas env vars en tu proyecto:
   - `KV_REST_API_URL`
   - `KV_REST_API_TOKEN`

> Si ya tenés KV, solo conéctalo al proyecto desde Storage → Connect to Project.

---

### Paso 3 — Variables de entorno (opcional)

En Vercel → Project Settings → Environment Variables:

| Variable | Valor |
|---|---|
| `TELEGRAM_TOKEN` | `8538242111:AAGPdp2z9BkcDmUGtpnBdgscyLvYSD_dxT0` |

Si no lo agregás, el código usa el token hardcodeado como fallback.

---

### Paso 4 — Registrar el Webhook de Telegram

Una vez desplegado, abrir este URL en el browser (una sola vez):

```
https://api.telegram.org/bot8538242111:AAGPdp2z9BkcDmUGtpnBdgscyLvYSD_dxT0/setWebhook?url=https://trading-different.vercel.app/api/webhook
```

Respuesta esperada: `{"ok":true,"result":true,"description":"Webhook was set"}`

---

### Paso 5 — Primer mensaje

Abrir Telegram → buscar **@DataDifferentbot** → mandar `/start`

El bot detecta tu Chat ID, lo guarda en KV, y queda listo para alertas.

---

## 📐 Arquitectura

```
Dashboard (browser)
    ├─ POST /api/sync     → guarda pools en KV
    └─ POST /api/alert    → envía alerta custom a Telegram

Vercel Cron
    ├─ /api/cron/check    → cada 5 min: precio + señal → Telegram
    └─ /api/cron/briefing → 8:00 AM BsAs (11:00 UTC): resumen diario

Telegram → POST /api/webhook → comandos: /precio /pools /estado /trade...
```

**Estado en Vercel KV:**
- `td:pools` — pools actuales (scalping + swing)
- `td:mode` — "scalping" | "swing"
- `td:trendiff` — "bullish" | "bearish"
- `td:chat_id` — tu chat ID de Telegram
- `td:alerts_sent` — cache anti-spam de alertas enviadas
- `td:trades_log` — log de trades registrados
- `td:trade:{chat_id}` — sesión temporal de /trade (expira 10 min)

---

## 💬 Comandos Telegram

| Comando | Descripción |
|---|---|
| `/precio` | Precio actual + señal activa |
| `/pools` | Lista de pools del modo actual |
| `/estado` | Resumen completo + botones inline |
| `/trade` | Registrar un trade (flujo conversacional) |
| `/scalping` | Cambiar a modo Scalping |
| `/swing` | Cambiar a modo Swing |
| `/bullish` | TrenDiff → ALCISTA |
| `/bearish` | TrenDiff → BAJISTA |
| `/ayuda` | Lista de comandos |

---

## ⚠️ Diferencias vs bot local (btc_bot.py)

| Función | Bot local | Bot Vercel |
|---|---|---|
| Alertas de precio | Cada 1 min | Cada 5 min (cron) |
| Gráfico en señal | ✅ matplotlib | ❌ sin imagen |
| Trades log | trades_log.json | Vercel KV cloud |
| Disponibilidad | Solo PC encendido | 24/7 en la nube |
