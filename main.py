import os
import time
import hmac
import hashlib
import requests
import datetime
import threading
from urllib.parse import urlencode
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "NY 18:00 SMC Auto-Trader Active!"

# TELEGRAM CONFIG
TELEGRAM_BOT_TOKEN = "7991139143:AAGMcCCTmgz_GdGFmwnmmWpWNgqXEv-C9t4"
TELEGRAM_CHAT_ID = "6340493480"

# FIXED RISK CONFIGURATION ($20 Risk Per Trade)
RISK_AMOUNT_USD = 20.0 

# BINANCE TESTNET API KEYS
BINANCE_TESTNET_API_KEY = os.environ.get("BINANCE_API_KEY", "YOUR_TESTNET_API_KEY_HERE")
BINANCE_TESTNET_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "YOUR_TESTNET_SECRET_KEY_HERE")

BASE_URL = "https://testnet.binancefuture.com"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def generate_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def post_order(params):
    """Binance API order placement handler"""
    endpoint = "/fapi/v1/order"
    params["timestamp"] = int(time.time() * 1000)
    query_string = urlencode(params)
    signature = generate_signature(query_string, BINANCE_TESTNET_SECRET_KEY)
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_TESTNET_API_KEY}
    return requests.post(url, headers=headers, timeout=10).json()

def calculate_quantity(risk_usd, entry_price, sl_price):
    """Dynamic Quantity/Lot calculation based on $20 risk limit"""
    price_diff = abs(entry_price - sl_price)
    if price_diff == 0:
        return 0.001
    
    # Calculate exact quantity to risk $20
    qty = risk_usd / price_diff
    return round(qty, 3)

def execute_trade(symbol, side, entry_price, sl_price, tp_price):
    try:
        quantity = calculate_quantity(RISK_AMOUNT_USD, entry_price, sl_price)
        
        if quantity <= 0:
            print("Invalid Quantity calculated.")
            return

        # 1. Market Entry Order
        entry_params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity
        }
        res_entry = post_order(entry_params)

        if "orderId" in res_entry:
            exit_side = "SELL" if side == "BUY" else "BUY"
            
            # 2. Stop Loss Order
            sl_params = {
                "symbol": symbol,
                "side": exit_side,
                "type": "STOP_MARKET",
                "stopPrice": sl_price,
                "closePosition": "true"
            }
            post_order(sl_params)

            # 3. Take Profit Order
            tp_params = {
                "symbol": symbol,
                "side": exit_side,
                "type": "TAKE_PROFIT_MARKET",
                "stopPrice": tp_price,
                "closePosition": "true"
            }
            post_order(tp_params)

            emoji = "🔴" if side == "SELL" else "🟢"
            msg = (
                f"{emoji} <b>NY 18:00 SMC TRADE EXECUTED!</b>\n\n"
                f"🪙 <b>Symbol:</b> #{symbol}\n"
                f"📊 <b>Side:</b> {side}\n"
                f"💵 <b>Risk Amount:</b> ${RISK_AMOUNT_USD}\n"
                f"🔢 <b>Calculated Qty:</b> {quantity}\n"
                f"🛑 <b>Stop Loss:</b> {sl_price}\n"
                f"🎯 <b>1:2 TP:</b> {tp_price}\n\n"
                f"⚡ <i>Entry, SL & TP Placed with Auto Risk Control!</i>"
            )
            send_telegram_alert(msg)
            print(f"Trade Success: {symbol} - {side} | Qty: {quantity}")
        else:
            print(f"Trade Order Failed: {res_entry}")
    except Exception as e:
        print(f"API Error: {e}")

def is_ny_18_session():
    utc_now = datetime.datetime.utcnow()
    ny_time = utc_now - datetime.timedelta(hours=4)
    
    if ny_time.hour == 18 or (ny_time.hour == 17 and ny_time.minute >= 50):
        return True
    return True # Set to True for paper trading test mode

def scan_ny_smc_setup(symbol="BTCUSDT"):
    url = f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=5m&limit=15"
    try:
        res = requests.get(url, timeout=10).json()
        if len(res) < 15:
            return

        closes = [float(k[4]) for k in res]
        highs = [float(k[2]) for k in res]
        lows = [float(k[3]) for k in res]

        current_close = closes[-1]

        swing_high = max(highs[-12:-4])
        swing_low = min(lows[-12:-4])

        # Fake Move UP -> Downside MSS -> SELL Setup
        fake_up = max(highs[-5:-1]) > swing_high
        mss_down = current_close < swing_low
        fvg_bearish = highs[-1] < lows[-3]

        if fake_up and mss_down and fvg_bearish and is_ny_18_session():
            extreme_ob_high = max(highs[-4:])
            sl = round(extreme_ob_high, 2)
            risk = sl - current_close
            if risk > 0:
                tp = round(current_close - (risk * 2.0), 2)
                execute_trade(symbol, "SELL", current_close, sl, tp)
                return

        # Fake Move DOWN -> Upside MSS -> BUY Setup
        fake_down = min(lows[-5:-1]) < swing_low
        mss_up = current_close > swing_high
        fvg_bullish = lows[-1] > highs[-3]

        if fake_down and mss_up and fvg_bullish and is_ny_18_session():
            extreme_ob_low = min(lows[-4:])
            sl = round(extreme_ob_low, 2)
            risk = current_close - sl
            if risk > 0:
                tp = round(current_close + (risk * 2.0), 2)
                execute_trade(symbol, "BUY", current_close, sl, tp)
                return

    except Exception as e:
        print(f"Scan Error: {e}")

def bot_loop():
    time.sleep(3)
    send_telegram_alert("🤖 <b>NY 18:00 SMC Auto-Trader Started ($20 Fixed Risk)!</b>")
    while True:
        scan_ny_smc_setup("BTCUSDT")
        time.sleep(300)

if __name__ == '__main__':
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
