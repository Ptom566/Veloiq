import os
import time
import requests
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "SMC Gold (PAXGUSDT) Paper Trader Active!"

# ---------------------------------------------------------------------------
# TELEGRAM CONFIG
# IMPORTANT: never hardcode secrets here. Set these in Render's dashboard:
# Render -> your service -> Environment -> Add Environment Variable
#   TELEGRAM_BOT_TOKEN = <your bot token>
#   TELEGRAM_CHAT_ID   = <your chat id>
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set. "
          "Set them in Render's Environment tab before deploying.")

# FIXED RISK CONFIGURATION ($20 Risk Per Trade)
RISK_AMOUNT_USD = 20.0

# PUBLIC BINANCE ENDPOINT (NO API KEY REQUIRED)
PUBLIC_BASE_URL = "https://fapi.binance.com"

# Active Trades Memory Storage
active_trades = []


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram disabled - no token set] {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Telegram API error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")


def is_ny_18_session():
    """
    Checks whether it's currently around the NY 6PM (18:00) session.
    NOTE: currently forced to always return True for backtest/demo purposes.
    Set FORCE_ALWAYS_ON = False below to enforce the real time-window check.
    """
    FORCE_ALWAYS_ON = True  # flip to False to restrict trading to the NY 18:00 window

    if FORCE_ALWAYS_ON:
        return True

    utc_now = datetime.now(timezone.utc)
    ny_time = utc_now - timedelta(hours=4)
    if ny_time.hour == 18 or (ny_time.hour == 17 and ny_time.minute >= 50):
        return True
    return False


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
        f"{emoji} <b>GOLD (PAXGUSDT) DEMO TRADE EXECUTED!</b>\n\n"
        f"🪙 <b>Symbol:</b> Gold (#{symbol})\n"
        f"📊 <b>Side:</b> {side}\n"
        f"💰 <b>Entry Price:</b> ${entry_price}\n"
        f"💵 <b>Risk Amount:</b> ${RISK_AMOUNT_USD}\n"
        f"🔢 <b>Calculated Lot/Qty:</b> {qty}\n"
        f"🛑 <b>Stop Loss:</b> ${sl_price}\n"
        f"🎯 <b>Take Profit (1:2):</b> ${tp_price}\n\n"
        f"🧪 <i>Gold SMC Backtest Mode Active</i>"
    )
    send_telegram_alert(msg)


def monitor_active_trades(current_price):
    global active_trades
    remaining_trades = []

    for trade in active_trades:
        side = trade["side"]
        sl = trade["sl"]
        tp = trade["tp"]

        if side == "BUY":
            if current_price >= tp:
                profit = round(RISK_AMOUNT_USD * 2.0, 2)
                msg = f"✅ <b>GOLD TRADE WON (+${profit})!</b>\nSymbol: #{trade['symbol']}\nTarget Hit at ${current_price}"
                send_telegram_alert(msg)
            elif current_price <= sl:
                msg = f"❌ <b>GOLD TRADE HIT SL (-${RISK_AMOUNT_USD})!</b>\nSymbol: #{trade['symbol']}\nSL Hit at ${current_price}"
                send_telegram_alert(msg)
            else:
                remaining_trades.append(trade)

        elif side == "SELL":
            if current_price <= tp:
                profit = round(RISK_AMOUNT_USD * 2.0, 2)
                msg = f"✅ <b>GOLD TRADE WON (+${profit})!</b>\nSymbol: #{trade['symbol']}\nTarget Hit at ${current_price}"
                send_telegram_alert(msg)
            elif current_price >= sl:
                msg = f"❌ <b>GOLD TRADE HIT SL (-${RISK_AMOUNT_USD})!</b>\nSymbol: #{trade['symbol']}\nSL Hit at ${current_price}"
                send_telegram_alert(msg)
            else:
                remaining_trades.append(trade)

    active_trades = remaining_trades


def scan_ny_smc_setup(symbol="PAXGUSDT"):
    url = f"{PUBLIC_BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=5m&limit=15"
    try:
        res = requests.get(url, timeout=10).json()
        if not isinstance(res, list) or len(res) < 15:
            print(f"Scan skipped: unexpected kline response: {res}")
            return

        closes = [float(k[4]) for k in res]
        highs = [float(k[2]) for k in res]
        lows = [float(k[3]) for k in res]

        current_close = closes[-1]

        monitor_active_trades(current_close)

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
    send_telegram_alert("🤖 <b>SMC Gold (PAXGUSDT) Paper Trader Started ($20 Risk)!</b>")
    while True:
        scan_ny_smc_setup("PAXGUSDT")
        time.sleep(300)


# ---------------------------------------------------------------------------
# TEST / DEBUG ROUTES - use these to verify the bot works without waiting
# ---------------------------------------------------------------------------

@app.route('/status')
def status():
    """See what the bot currently thinks its active trades are."""
    return jsonify({
        "active_trades": active_trades,
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    })


@app.route('/test-alert')
def test_alert():
    """Fire a plain test message to Telegram to confirm the bot/chat id work."""
    send_telegram_alert("✅ Test alert from your bot - Telegram connection is working!")
    return jsonify({"sent": True})


@app.route('/test-trade')
def test_trade():
    """
    Manually trigger a fake BUY trade so you can see the full alert
    format + win/loss flow without waiting for a real SMC setup.
    """
    entry = 2400.0
    sl = 2390.0
    tp = 2420.0
    execute_paper_trade("PAXGUSDT", "BUY", entry, sl, tp)
    return jsonify({"triggered": True, "entry": entry, "sl": sl, "tp": tp})


@app.route('/scan-now')
def scan_now():
    """Force an immediate real scan against live Binance data (instead of waiting 5 min)."""
    scan_ny_smc_setup("PAXGUSDT")
    return jsonify({"scanned": True, "active_trades": active_trades})


if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        t = threading.Thread(target=bot_loop)
        t.daemon = True
        t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
