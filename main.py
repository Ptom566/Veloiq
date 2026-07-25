import requests
import time
import threading
import os
from flask import Flask

# Flask Server for Render Health Check
app = Flask(__name__)

@app.route('/')
def home():
    return "OI Accumulation Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# TELEGRAM BOT CONFIG
TELEGRAM_BOT_TOKEN = "7991139143:AAGMcCCTmgz_GdGFmwnmmWpWNgqXEv-C9t4"
TELEGRAM_CHAT_ID = "6340493480"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending alert: {e}")

def get_binance_oi_accumulation():
    ticker_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(ticker_url, timeout=10)
        if response.status_code == 200:
            tickers = response.json()
            
            for coin in tickers:
                symbol = coin.get("symbol", "")
                if symbol.endswith("USDT"):
                    price_change = float(coin.get("priceChangePercent", 0))
                    volume = float(coin.get("quoteVolume", 0))

                    # Filter: High Volume ($30M+) and Low Price Movement (-2.5% to +2.5%)
                    if volume >= 30000000 and abs(price_change) <= 2.5:
                        # Fetch Open Interest Data
                        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
                        oi_res = requests.get(oi_url, timeout=5)
                        
                        if oi_res.status_code == 200:
                            oi_data = oi_res.json()
                            open_interest = float(oi_data.get("openInterest", 0))
                            last_price = float(coin.get("lastPrice", 1))
                            oi_value_usdt = open_interest * last_price

                            # Telegram Alert Message
                            msg = (
                                f"🔥 <b>INSTITUTIONAL ACCUMULATION DETECTED!</b>\n\n"
                                f"🪙 <b>Coin:</b> #{symbol}\n"
                                f"📊 <b>24h Price Change:</b> {price_change:.2f}%\n"
                                f"💰 <b>24h Volume:</b> ${volume/1000000:.2f}M\n"
                                f"📈 <b>Open Interest (OI):</b> ${oi_value_usdt/1000000:.2f}M\n\n"
                                f"⚡ <i>Smart Money Building Position! Big move expected soon.</i>"
                            )
                            send_telegram_alert(msg)
                            print(f"Accumulation Alert Sent: {symbol}")
                            time.sleep(1) # Prevent API Rate Limit
    except Exception as e:
        print(f"Error checking OI: {e}")

def bot_loop():
    time.sleep(3)
    send_telegram_alert("🤖 <b>OI & Accumulation Scanner Started Successfully!</b>")
    while True:
        get_binance_oi_accumulation()
        time.sleep(300) # Scan every 5 minutes

if __name__ == '__main__':
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    run_flask()
