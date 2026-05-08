# Estrategia Trading Different — Manual Operativo Completo

## ¿Cómo funciona la señal de entrada?

La estrategia se basa en un principio simple: **el precio de Bitcoin es atraído hacia donde hay mayor concentración de liquidez**. Esa liquidez son los stop-losses y liquidaciones de otros traders que están acumuladas en rangos de precio específicos (los "pools").

Cuando el precio toca uno de esos pools, dos cosas pueden pasar: o bien lo *limpia* (squeeze) y sigue de largo, o bien *rebota* desde él. El sistema busca ese rebote.

---

## Los 4 Pilares de la Estrategia

### 1. Identificación del Pool (Trigger de Precio)

Los pools se clasifican por intensidad de liquidez (color = tamaño estimado en millones de dólares):

| Color | Tamaño aprox. | Comportamiento esperado |
|-------|--------------|------------------------|
| 🔴 Rojo | > $100M | Muy fuerte atracción, rebote probable |
| 🟠 Naranja | $50–100M | Fuerte, buen riesgo/beneficio |
| 🟡 Amarillo | $20–50M | Medio, usar solo con confluencias |
| 🟢 Verde | < $20M | Débil, evitar operar solo |

**Regla**: Solo operar pools **rojo y naranja** de forma independiente. Los amarillos necesitan al menos una confluencia macro o de microestructura para ser válidos.

### 2. Filtro Macro (Contexto de EE.UU.)

Antes de entrar, el contexto macroeconómico debe ser favorable:

**Eventos de ALTA VOLATILIDAD — NO operar 30 min antes ni 15 min después:**
- CPI (Índice de Precios al Consumidor)
- Decisión de tasas de la FED (FOMC)
- NFP / Payrolls (primer viernes del mes)
- PIB trimestral de EE.UU.

**Correlaciones a monitorear:**
- Si DXY (dólar) está subiendo fuertemente → presión bajista para BTC → priorizar pools SHORT
- Si SPX/SPY está cayendo → riesgo-off → operar pools SHORT con más convicción
- Si DXY baja + SPX sube → entorno risk-on → priorizar pools LONG

**TrenDiff (sesgo del grupo):** Es el filtro de dirección macro del Discord. Si está en BULLISH, se priorizan los pools LONG y se ignoran los SHORT débiles, y viceversa.

### 3. Confirmación de Microestructura (1m / 5m)

Cuando el precio llega al pool, NO se entra de inmediato. Se espera confirmación en temporalidades bajas:

**Señales de entrada válidas al tocar el pool:**
1. **Vela de absorción**: vela con mecha larga que penetra el pool pero cierra dentro de él → señal de rechazo
2. **Divergencia de volumen**: el precio toca el pool pero el volumen de ventas (en pool LONG) es decreciente
3. **CLD — Cumulative Liquidation Delta**: si el CLD muestra que las liquidaciones del pool ya fueron ejecutadas (delta acumulado baja bruscamente y estabiliza), el pool está "limpio" y se puede entrar en la dirección opuesta

**Entrar en 1m cuando:**
- Cierre de vela 1m por encima del borde inferior del pool (para LONG)
- Cierre de vela 1m por debajo del borde superior del pool (para SHORT)

### 4. Gestión de la Operación

**Stop Loss:** 0.3% más allá del borde del pool.
- Pool LONG con borde bajo en $94,000 → SL en $93,718
- Pool SHORT con borde alto en $96,500 → SL en $96,789

**Take Profit:** El pool opuesto más cercano.
- Si estás LONG desde $94,000 y el pool SHORT más cercano está en $96,200 → TP en $96,200
- R:R mínimo aceptable: **1.5:1** (el TP debe ser al menos 1.5 veces el riesgo)

**Salida anticipada si:**
- El CLD muestra un delta explosivo en tu contra → señal de squeeze
- El precio penetra más del 60% del pool sin rebotar → probable limpieza, salir al SL

---

## El Patrón "Squeeze" — Cuándo el Pool se Limpia

Un **squeeze** ocurre cuando el precio NO rebota desde el pool sino que lo atraviesa, liquidando a todos los traders que entraron en él.

**Señales de que se viene un Squeeze (no entrar o salir rápido):**
1. El precio llega al pool con velas grandes y de alto volumen → momentum fuerte, no hay absorción
2. El precio ya visitó ese pool antes en las últimas 4–8 horas → fue parcialmente limpiado, está más débil
3. El CLD sigue aumentando en la misma dirección al tocar el pool → no hay rechazo, hay continuación
4. El pool está en la dirección del trend mayor (diario/semanal) → el mercado "en tendencia" hace squeezes frecuentes

**Qué hacer si se confirma Squeeze:**
- Invertir la lógica: si era un pool LONG que esperabas rebotar, al ver squeeze → el TP del squeeze está en el siguiente pool SHORT
- Esto es una operación de riesgo mayor, solo para traders experimentados

---

## Algoritmo de Decisión — Lógica Si/Entonces

```
CONDICIÓN 1 — Precio cerca del pool
  SI precio <= pool_long.high + 0.5% 
  O  precio >= pool_short.low - 0.5%
  → ACTIVAR MONITOREO

CONDICIÓN 2 — Filtro macro OK
  SI evento_macro_en_curso = FALSO  (no hay CPI/FOMC/NFP activo)
  Y  DXY_tendencia != CONTRA_DIRECCION_TRADE
  → PASAR AL SIGUIENTE FILTRO

CONDICIÓN 3 — TrenDiff alineado
  SI trade_direccion = 'LONG' Y trendiff = 'BULLISH'
  O  trade_direccion = 'SHORT' Y trendiff = 'BEARISH'
  O  pool_intensidad = 'RED' (pool rojo ignora trendiff débil)
  → PASAR AL SIGUIENTE FILTRO

CONDICIÓN 4 — Confirmación de microestructura (1m/5m)
  SI pool_tipo = 'LONG':
    ESPERAR cierre_vela_1m > pool.low + (pool.high - pool.low) * 0.3
    Y volumen_bajista_decreciente = VERDADERO
    O CLD_delta_estabilizado = VERDADERO
  SI pool_tipo = 'SHORT':
    ESPERAR cierre_vela_1m < pool.high - (pool.high - pool.low) * 0.3
    Y volumen_alcista_decreciente = VERDADERO
  → EJECUTAR ENTRADA

ENTRADA EJECUTADA:
  precio_entrada = precio_actual
  SL = pool.low * 0.997  (para LONG)
     = pool.high * 1.003 (para SHORT)
  TP = pool_opuesto_más_cercano.mid
  riesgo_USD = capital * risk_pct / 100
  pip_risk = abs(precio_entrada - SL)
  tamanio_posicion = riesgo_USD / (pip_risk / precio_entrada)
  apalancamiento = floor(precio_entrada / (pip_risk * 1.4))

GESTIÓN EN VIVO:
  SI precio_penetra > 60% del pool SIN rebotar:
    → SALIR (probable squeeze en curso)
  SI CLD_explota en contra:
    → SALIR preventivamente
  SI precio_llega_a_TP:
    → CERRAR posición completa
    → Registrar pool como "limpiado" por las próximas 8h
```

---

## Flujo Operativo Paso a Paso

**Paso 1 — Revisión matutina (08:00 BsAs)**
Abrir el dashboard. Verificar el calendario macro: ¿hay eventos de alta volatilidad hoy? Marcar horarios de no-operación.

**Paso 2 — Orientar el sesgo (TrenDiff)**
Revisar la estructura diaria/semanal de BTC. ¿El mercado está sobre o bajo el VWAP semanal? Configurar TrenDiff en BULLISH o BEARISH según la estructura macro.

**Paso 3 — Identificar pools activos**
Revisar el Mapa de Liquidaciones del dashboard. Identificar el pool rojo/naranja más cercano al precio actual (tanto por arriba como por abajo). Estos son los "targets" para la sesión.

**Paso 4 — Esperar el toque**
No adelantarse. El precio debe llegar al pool. Una vez que lo toca, bajar a 1m/5m para la confirmación.

**Paso 5 — Confirmar y entrar**
Esperar la vela de absorción o el estabilizamiento del CLD. Colocar entrada, SL y TP usando la Calculadora del dashboard.

**Paso 6 — Gestionar y registrar**
Monitorear en 1m. Si el pool se limpia, aceptar el SL sin dudar. Si llega al TP, tomar la ganancia completa. Registrar el resultado.

---

## Reglas Inmutables

1. **Un trade a la vez.** No abrir segunda posición mientras hay una abierta.
2. **Máximo 1–2% del capital por operación.**
3. **Si perdiste 3 trades seguidos, parar el día.** El mercado no está respondiendo a los pools ese día.
4. **Nunca mover el SL en contra.** Si el precio va hacia el SL, dejarlo ejecutar.
5. **Pool visitado recientemente = pool débil.** Si el precio ya tocó ese nivel en las últimas 4–8h, reducir el tamaño de la posición a la mitad o ignorarlo.
6. **30 minutos antes de un dato macro = zona de no-trade.** Sin excepciones.

---

## Traducción a Código (Python / Pine Script)

### Python — Señal básica

```python
def get_signal(price, pools, trendiff, macro_active=False):
    if macro_active:
        return None  # No operar durante datos macro

    for pool in pools:
        # Precio dentro del 0.5% del pool
        if pool['low'] * 0.995 <= price <= pool['high'] * 1.005:
            direction = pool['side']  # 'LONG' o 'SHORT'
            
            # Filtro TrenDiff
            if trendiff == 'BULLISH' and direction == 'SHORT' and pool['intensity'] != 'red':
                continue
            if trendiff == 'BEARISH' and direction == 'LONG' and pool['intensity'] != 'red':
                continue
            
            pip_risk = abs(price - (pool['low'] if direction == 'LONG' else pool['high']))
            sl = pool['low'] * 0.997 if direction == 'LONG' else pool['high'] * 1.003
            
            # Buscar TP en pool opuesto
            opposite = [p for p in pools if p['side'] != direction]
            if not opposite:
                continue
            tp_pool = min(opposite, key=lambda p: abs((p['low']+p['high'])/2 - price))
            tp = (tp_pool['low'] + tp_pool['high']) / 2
            
            rr = abs(tp - price) / abs(sl - price)
            if rr < 1.5:
                continue  # R:R insuficiente
            
            return {
                'direction': direction,
                'entry': price,
                'sl': sl,
                'tp': tp,
                'rr': round(rr, 2),
                'pool': pool['label']
            }
    return None
```

### Pine Script — Alerta de toque de pool

```pine
//@version=5
indicator("Pool Alerts TD", overlay=true)

// Configurar niveles manualmente
pool_long_low  = input.float(94000, "Pool LONG - Low")
pool_long_high = input.float(94800, "Pool LONG - High")
pool_short_low = input.float(96200, "Pool SHORT - Low")
pool_short_high= input.float(97000, "Pool SHORT - High")

// Detección de toque
long_touch  = low  <= pool_long_high  and low  >= pool_long_low  * 0.997
short_touch = high >= pool_short_low  and high <= pool_short_high * 1.003

// Confirmación: cierre dentro del pool (absorción)
long_confirm  = long_touch  and close > pool_long_low
short_confirm = short_touch and close < pool_short_high

// Visualización
bgcolor(long_touch  ? color.new(color.green,  85) : na)
bgcolor(short_touch ? color.new(color.red,    85) : na)

plotshape(long_confirm,  style=shape.triangleup,   location=location.belowbar, color=color.lime,  size=size.small)
plotshape(short_confirm, style=shape.triangledown, location=location.abovebar, color=color.red,   size=size.small)

// Alertas
alertcondition(long_confirm,  "Pool LONG Touch + Confirm",  "BTC toca pool LONG - confirmar entrada")
alertcondition(short_confirm, "Pool SHORT Touch + Confirm", "BTC toca pool SHORT - confirmar entrada")
```

---

*Actualizado: Abril 2026 | Proyecto Trading Different*
