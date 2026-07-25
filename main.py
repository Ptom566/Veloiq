import os
import time
import requests
import datetime
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "SMC Paper Trading Bot is Running!"

# TELEGRAM CONFIG
TELEGRAM_BOT_TOKEN = "7991139143:AAGMcCCTmgz_GdGFmwnmmWpWNgqXEv-C9t4"
TELEGRAM_CHAT_ID = "6340493480"

RISK_AMOUNT_USD = 20.0

# PUBLIC BINANCE ENDPOINT (NO API KEY NEEDED)
PUBLIC_BASE_URL = "https://fapi.binance.com"

# Active Trades Memory Storage
active_trades = []

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def is_ny_18_session():
    utc_now = datetime.datetime.utcnow()
    ny_time = utc_now - datetime.timedelta(hours=4)
    if ny_time.hour == 18 or (ny_time.hour == 17 and ny_time.minute >= 50):
        return True
    return True # Always active for paper trading testing

def execute_paper_trade(symbol, side, entry_price, sl_price, tp_price):
    price_diff = abs(entry_price - sl_price)
    if price_diff == 0:
        return
    
    qty = round(RISK_AMOUNT_USD / price_diff, 3)
    
    trade = {
        "symbol": symbol,
        "side": side,
        "entry": entry_price,
        "sl": sl_price,
        "tp": tp_price,
        "qty": qty
    }
    active_trades.append(trade)

    emoji = "🔴" if side == "SELL" else "🟢"
    msg = (
        f"{emoji} <b>SIMULATED DEMO TRADE EXECUTED!</b>\n\n"
        f"🪙 <b>Symbol:</b> #{symbol}\n"
        f"📊 <b>Side:</b> {side}\n"
        f"💰 <b>Entry Price:</b> {entry_price}\n"
        f"💵 <b>Risk Amount:</b> ${RISK_AMOUNT_USD}\n"
        f"🔢 <b>Calculated Lot/Qty:</b> {qty}\n"
        f"🛑 <b>Stop Loss:</b> {sl_price}\n"
        f"🎯 <b>Take Profit (1:2):</b> {tp_price}\n\n"
        f"🧪 <i>Paper Trading Mode Active</i>"
    )
    send_telegram_alert(msg)

def monitor_active_trades(current_price):
    global active_trades
    remaining_trades = []
    
    for trade in active_trades:
        side = trade["side"]
        sl = trade["sl"]
        tp = trade["tp"]
        
        # Check Win/Loss for BUY
        if side == "BUY":
            if current_price >= tp:
                profit = round(RISK_AMOUNT_USD * 2.0, 2)
                msg = f"✅ <b>DEMO TRADE WON (+${profit})!</b>\nSymbol: #{trade['symbol']}\nTarget Hit at {current_price}"
                send_telegram_alert(msg)
            elif current_price <= sl:
                msg = f"❌ <b>DEMO TRADE HIT SL (-${RISK_AMOUNT_USD})!</b>\nSymbol: #{trade['symbol']}\nSL Hit at {current_price}"
                send_telegram_alert(msg)
            else:
                remaining_trades.append(trade)
                
        # Check Win/Loss for SELL
        elif side == "SELL":
            if current_price <= tp:
                profit = round(RISK_AMOUNT_USD * 2.0, 2)
                msg = f"✅ <b>DEMO TRADE WON (+${profit})!</b>\nSymbol: #{trade['symbol']}\nTarget Hit at {current_price}"
                send_telegram_alert(msg)
            elif current_price >= sl:
                msg = f"❌ <b>DEMO TRADE HIT SL (-${RISK_AMOUNT_USD})!</b>\nSymbol: #{trade['symbol']}\nSL Hit at {current_price}"
                send_telegram_alert(msg)
            else:
                remaining_trades.append(trade)

    active_trades = remaining_trades

def scan_ny_smc_setup(symbol="BTCUSDT"):
    url = f"{PUBLIC_BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=5m&limit=15"
    try:
        res = requests.get(url, timeout=10).json()
        if len(res) < 15:
            return

        closes = [float(k[4]) for k in res]
        highs = [float(k[2]) for k in res]
        lows = [float(k[3]) for k in res]

        current_close = closes[-1]
        
        # Monitor ongoing paper trades
        monitor_active_trades(current_close)

        # Avoid multiple entries if trade is active
        if len(active_trades) > 0:
            return

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
                execute_paper_trade(symbol, "SELL", current_close, sl, tp)
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
                execute_paper_trade(symbol, "BUY", current_close, sl, tp)
                return

    except Exception as e:
        print(f"Scan Error: {e}")

def bot_loop():
    time.sleep(3)
    send_telegram_alert("🤖 <b>SMC Paper Trader Active (No API Key Required)!</b>")
    while True:
        scan_ny_smc_setup("BTCUSDT")
        time.sleep(300)

if __name__ == '__main__':
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
