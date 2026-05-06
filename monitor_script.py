import os
import time
import logging
import requests
from datetime import datetime
import pytz

# ─── Configuración ────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_BOT_TOKEN_AQUI")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "TU_CHAT_ID_AQUI")

PRICE_MEDIUM   = 1.30   # Alerta nivel medio
PRICE_PRIORITY = 1.25   # Alerta prioritaria

CHECK_INTERVAL = 60     # Segundos entre cada consulta de precio

TIMEZONE = pytz.timezone("America/Mexico_City")
REPORT_HOURS = {7, 20}  # 7:00 AM y 8:00 PM hora México

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Estado interno ───────────────────────────────────────────────────────────
last_alert_sent = None        # "medium" | "priority" | None
last_report_hour_sent = None  # (fecha, hora) para evitar reporte duplicado


def get_xrp_price():
    """Obtiene el precio actual de XRP en USD desde CoinGecko (gratis, sin API key)."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "ripple", "vs_currencies": "usd"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()["ripple"]["usd"]
    except Exception as exc:
        log.error("Error obteniendo precio: %s", exc)
        return None


def send_telegram(message):
    """Envía un mensaje vía Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("Telegram OK - mensaje enviado")
        return True
    except Exception as exc:
        log.error("Error enviando Telegram: %s", exc)
        return False


def check_daily_report(price):
    """Envía reporte diario a las 7:00 AM y 8:00 PM hora México."""
    global last_report_hour_sent

    now_mx = datetime.now(TIMEZONE)
    current_hour = now_mx.hour
    today = now_mx.date()
    key = (today, current_hour)

    if current_hour in REPORT_HOURS and last_report_hour_sent != key:
        period = "🌅 Reporte Matutino" if current_hour == 7 else "🌙 Reporte Nocturno"
        now_str = now_mx.strftime("%d/%m/%Y %H:%M:%S")

        # Indicador visual según precio
        if price < PRICE_PRIORITY:
            indicator = "🔴 Por debajo del umbral prioritario"
        elif price < PRICE_MEDIUM:
            indicator = "🟡 Por debajo del umbral medio"
        else:
            indicator = "🟢 Precio estable"

        msg = (
            f"📊 *{period} — XRP*\n"
            f"Precio actual: `${price:.4f} USD`\n"
            f"Estado: {indicator}\n"
            f"Umbral medio: `${PRICE_MEDIUM} USD`\n"
            f"Umbral prioritario: `${PRICE_PRIORITY} USD`\n"
            f"🕐 {now_str} (Ciudad de México)"
        )
        send_telegram(msg)
        last_report_hour_sent = key
        log.info("Reporte diario enviado — hora: %d:00", current_hour)


def check_and_alert(price):
    global last_alert_sent

    now = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

    if price < PRICE_PRIORITY:
        level = "priority"
        if last_alert_sent != "priority":
            msg = (
                f"🚨 *ALERTA PRIORITARIA — XRP*\n"
                f"Precio actual: `${price:.4f} USD`\n"
                f"Por debajo del umbral prioritario de `${PRICE_PRIORITY} USD`\n"
                f"🕐 {now} (Ciudad de México)"
            )
            send_telegram(msg)
            last_alert_sent = level
            log.warning("Alerta PRIORITARIA enviada — precio: $%.4f", price)

    elif price < PRICE_MEDIUM:
        level = "medium"
        if last_alert_sent not in ("medium", "priority"):
            msg = (
                f"⚠️ *Alerta Nivel Medio — XRP*\n"
                f"Precio actual: `${price:.4f} USD`\n"
                f"Por debajo del umbral de `${PRICE_MEDIUM} USD`\n"
                f"🕐 {now} (Ciudad de México)"
            )
            send_telegram(msg)
            last_alert_sent = level
            log.info("Alerta MEDIA enviada — precio: $%.4f", price)

    else:
        if last_alert_sent is not None:
            msg = (
                f"✅ *XRP recuperado*\n"
                f"Precio actual: `${price:.4f} USD`\n"
                f"De nuevo por encima de `${PRICE_MEDIUM} USD`\n"
                f"🕐 {now} (Ciudad de México)"
            )
            send_telegram(msg)
            log.info("Precio recuperado — alerta reseteada")
        last_alert_sent = None


def main():
    log.info("Monitor XRP iniciado — revisando cada %ds", CHECK_INTERVAL)
    log.info("Umbrales: Medio=$%.2f | Prioritario=$%.2f", PRICE_MEDIUM, PRICE_PRIORITY)
    log.info("Reportes diarios: 7:00 AM y 8:00 PM (Ciudad de México)")

    while True:
        price = get_xrp_price()
        if price is not None:
            log.info("XRP: $%.4f USD", price)
            check_daily_report(price)
            check_and_alert(price)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()