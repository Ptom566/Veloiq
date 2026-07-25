import requests
import time

# --- TELEGRAM BOT CONFIG ---
TELEGRAM_BOT_TOKEN = "7991139143:AAGMcCCTmgz_GdGFmwnmmWpWNgqXEv-C9t4"
TELEGRAM_CHAT_ID = "6340493480"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Telegram API Response: {response.status_code}")
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
                    
                    # High Volume Accumulation Condition
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
        print(f"Error fetching Binance data: {e}")

if __name__ == '__main__':
    print("Starting Bot Loop...")
    send_telegram_alert("🤖 <b>Crypto Scanner Bot Started Successfully on Render!</b>")
    
    while True:
        check_binance_oi()
        time.sleep(300) # Check every 5 minutes
