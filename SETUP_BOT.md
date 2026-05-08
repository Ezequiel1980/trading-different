# Setup — Trading Different BTC Bot + Dashboard

## 📊 Dashboard Web (dashboard.html)
Abrí el archivo directamente en Chrome — no necesita servidor ni instalación.

## 🤖 Bot de Telegram (btc_bot.py)

### Paso 1: Instalar Python (si no tenés)
https://www.python.org/downloads/ — descargar Python 3.10+

### Paso 2: Instalar dependencias
Abrir terminal/cmd y ejecutar:
```
pip install requests schedule pytz python-telegram-bot
```

### Paso 3: Activar el bot ✅ YA CONFIGURADO
El bot @DataDifferentbot ya está configurado con su token.
El Chat ID se detecta automáticamente.

### Paso 4: Ejecutar
```
python btc_bot.py
```
Cuando arranque, abrí Telegram → buscá *@DataDifferentbot* → mandá `/start`.
El bot detecta tu Chat ID automáticamente y te lo confirma.

### Comandos disponibles en Telegram:
- /precio   → precio actual + señal
- /pools    → pools activos
- /estado   → resumen completo
- /scalping → cambiar a modo scalping
- /swing    → cambiar a modo swing
- /bullish  → TrenDiff alcista
- /bearish  → TrenDiff bajista
- /ayuda    → lista de comandos

## 🔄 Actualizar los niveles de pools
Los pools se actualizan manualmente revisando el dashboard de Trading Different.
- En el dashboard web: botón "✏️ Editar niveles" 
- En el bot: editar la variable POOLS en btc_bot.py
