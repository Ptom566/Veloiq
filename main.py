import requests
import time
import threading
import os
from flask import Flask

# Flask Server for Render Health Check
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# TELEGRAM BOT LOGIC
TELEGRAM_BOT_TOKEN = "7991139143:AAGMcCCTmgz_GdGFmwnmmWpWNgqXEv-C9t4"
TELEGRAM_CHAT_ID = "6340493480"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending alert: {e}")

def check_binance_oi():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for coin in data:
                symbol = coin.get("symbol", "")
                if symbol.endswith("USDT"):
                    price_change = float(coin.get("priceChangePercent", 0))
                    volume = float(coin.get("quoteVolume", 0))
                    
                    if volume >= 50000000 and abs(price_change) <= 2.0:
                        msg = (
                            f"🚨 <b>SMART MONEY ACCUMULATION ALERT!</b>\n\n"
                            f"🪙 <b>Coin:</b> {symbol}\n"
                            f"📊 <b>24h Price Change:</b> {price_change:.2f}%\n"
                            f"💰 <b>24h Volume:</b> ${volume/1000000:.2f}M\n\n"
                            f"💡 <i>High Volume Accumulation Detected!</i>"
                        )
                        send_telegram_alert(msg)
                        print(f"Alert Sent for {symbol}!")
    except Exception as e:
        print(f"Error: {e}")

def bot_loop():
    send_telegram_alert("🤖 <b>Crypto Scanner Bot Started Successfully on Render!</b>")
    while True:
        check_binance_oi()
        time.sleep(300)

if __name__ == '__main__':
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    run_flask()
