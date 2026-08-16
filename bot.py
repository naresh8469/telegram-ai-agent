"""
bot_engine.py  (v3 â€” per-symbol strategy config)
Core strategy logic + paper trading simulation, with state saved to a
local SQLite database so it survives restarts on the cloud server.

Two strategies now run side by side, picked per symbol:
1. NSE indices (Nifty 50, Bank Nifty): 5-minute candles, EMA9 x EMA21
   crossover CONFIRMED by RSI(14). Trades only during NSE market hours,
   force-squared-off by 3:15 PM.
2. Crypto (Bitcoin, Ethereum) and Forex (EUR/USD, GBP/USD): 1-minute
   candles, EMA9 x EMA15 crossover with NO RSI filter (pure crossover).
   Crypto trades 24/7, forex trades ~24/5.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, time
import pytz

IST = pytz.timezone("Asia/Kolkata")
DB_PATH = "trading_bot.db"

RSI_PERIOD = 14
RSI_BUY_THRESHOLD = 50
RSI_SELL_THRESHOLD = 50
SQUARE_OFF_TIME = time(15, 15)     # NSE only
MARKET_OPEN = time(9, 15)          # NSE only
MARKET_CLOSE = time(15, 30)        # NSE only

# Per-symbol configuration.
TICKERS = {
    "NIFTY":     {"symbol": "^NSEI",    "market": "nse",    "timeframe": "5m", "ema_fast": 9, "ema_slow": 21, "use_rsi": True,  "stop_loss_pct": 0.30, "target_pct": 0.60, "capital": 100000},
    "BANKNIFTY": {"symbol": "^NSEBANK", "market": "nse",    "timeframe": "5m", "ema_fast": 9, "ema_slow": 21, "use_rsi": True,  "stop_loss_pct": 0.30, "target_pct": 0.60, "capital": 100000},
    "BITCOIN":   {"symbol": "BTC-USD",  "market": "crypto", "timeframe": "1m", "ema_fast": 9, "ema_slow": 15, "use_rsi": False, "stop_loss_pct": 0.80, "target_pct": 1.60, "capital": 100000},
    "ETHEREUM":  {"symbol": "ETH-USD",  "market": "crypto", "timeframe": "1m", "ema_fast": 9, "ema_slow": 15, "use_rsi": False, "stop_loss_pct": 1.00, "target_pct": 2.00, "capital": 100000},
    "EURUSD":    {"symbol": "EURUSD=X", "market": "forex",  "timeframe": "1m", "ema_fast": 9, "ema_slow": 15, "use_rsi": False, "stop_loss_pct": 0.15, "target_pct": 0.30, "capital": 100000},
    "GBPUSD":    {"symbol": "GBPUSD=X", "market": "forex",  "timeframe": "1m", "ema_fast": 9, "ema_slow": 15, "use_rsi": False, "stop_loss_pct": 0.15, "target_pct": 0.30, "capital": 100000},
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            entry_time TEXT,
            entry_price REAL,
            exit_time TEXT,
            exit_price REAL,
            pnl_pct REAL,
            pnl_rupees REAL,
            exit_reason TEXT,
            status TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_status(symbol, message):
    print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] [{symbol}] {message}", flush=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO status_log (timestamp, symbol, message) VALUES (?, ?, ?)",
        (datetime.now(IST).isoformat(), symbol, message),
    )
    conn.commit()
    conn.close()


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def fetch_latest_data(ticker, timeframe, ema_fast_period, ema_slow_period, use_rsi):
    import yfinance as yf
    # 1-minute data: Yahoo only keeps ~7 days of history, so request a
    # short window. 5-minute data can safely request a bit more.
    period = "5d" if timeframe == "1m" else "5d"
    df = yf.download(ticker, period=period, interval=timeframe, progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    df = df.tz_convert(IST)
    df["ema_fast"] = df["Close"].ewm(span=ema_fast_period, adjust=False).mean()
    df["ema_slow"] = df["Close"].ewm(span=ema_slow_period, adjust=False).mean()
    if use_rsi:
        df["rsi"] = calculate_rsi(df["Close"], RSI_PERIOD)
    return df


def get_open_position(symbol):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, side, entry_time, entry_price FROM trades WHERE symbol=? AND status='OPEN'",
        (symbol,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "side": row[1], "entry_time": row[2], "entry_price": row[3]}
    return None


def open_position(symbol, side, price, ts):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO trades (symbol, side, entry_time, entry_price, status) VALUES (?, ?, ?, ?, 'OPEN')",
        (symbol, side, ts.isoformat(), price),
    )
    conn.commit()
    conn.close()
    log_status(symbol, f"Opened {side} at {price:.4f}")


def close_position(trade_id, symbol, exit_price, ts, reason, pnl_pct, pnl_rupees):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE trades SET exit_time=?, exit_price=?, exit_reason=?, pnl_pct=?, pnl_rupees=?, status='CLOSED'
        WHERE id=?
    """, (ts.isoformat(), exit_price, reason, pnl_pct, pnl_rupees, trade_id))
    conn.commit()
    conn.close()
    log_status(symbol, f"Closed ({reason}) at {exit_price:.4f}, P&L Rs {pnl_rupees:.2f}")


def market_is_open(market_type, now_ist):
    if market_type == "crypto":
        return True  # 24/7
    if market_type == "forex":
        return now_ist.weekday() != 5  # closed Saturday (simplified)
    if market_type == "nse":
        if now_ist.weekday() >= 5:
            return False
        return MARKET_OPEN <= now_ist.time() <= MARKET_CLOSE
    return False


def check_and_trade(symbol_key):
    config = TICKERS[symbol_key]
    ticker = config["symbol"]
    market_type = config["market"]
    timeframe = config["timeframe"]
    ema_fast_period = config["ema_fast"]
    ema_slow_period = config["ema_slow"]
    use_rsi = config["use_rsi"]
    stop_loss_pct = config["stop_loss_pct"]
    target_pct = config["target_pct"]
    capital = config["capital"]

    now = datetime.now(IST)

    if not market_is_open(market_type, now):
        return

    df = fetch_latest_data(ticker, timeframe, ema_fast_period, ema_slow_period, use_rsi)
    if df is None or len(df) < ema_slow_period + 2:
        log_status(symbol_key, "No data / not enough candles yet")
        return

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(latest["Close"])

    position = get_open_position(symbol_key)

    # --- Manage existing position ---
    if position:
        if position["side"] == "BUY":
            pnl_pct = (price - position["entry_price"]) / position["entry_price"] * 100
        else:
            pnl_pct = (position["entry_price"] - price) / position["entry_price"] * 100

        exit_reason = None
        if market_type == "nse" and now.time() >= SQUARE_OFF_TIME:
            exit_reason = "Intraday square-off"
        elif pnl_pct <= -stop_loss_pct:
            exit_reason = "Stop-loss hit"
        elif pnl_pct >= target_pct:
            exit_reason = "Target hit"

        if exit_reason:
            pnl_rupees = capital * (pnl_pct / 100)
            close_position(position["id"], symbol_key, price, now, exit_reason, pnl_pct, pnl_rupees)
        return

    # --- Look for new entry ---
    crossed_up = prev["ema_fast"] <= prev["ema_slow"] and latest["ema_fast"] > latest["ema_slow"]
    crossed_down = prev["ema_fast"] >= prev["ema_slow"] and latest["ema_fast"] < latest["ema_slow"]

    if use_rsi:
        rsi_val = latest["rsi"]
        buy_ok = crossed_up and rsi_val > RSI_BUY_THRESHOLD
        sell_ok = crossed_down and rsi_val < RSI_SELL_THRESHOLD
        info = f"Price {price:.4f}, RSI {rsi_val:.1f}"
    else:
        buy_ok = crossed_up
        sell_ok = crossed_down
        info = f"Price {price:.4f}"

    if buy_ok:
        open_position(symbol_key, "BUY", price, now)
    elif sell_ok:
        open_position(symbol_key, "SELL", price, now)
    else:
        log_status(symbol_key, f"No signal. {info}")


def run_symbols(symbol_keys, label):
    print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] Scheduler tick ({label}) â€” checking {len(symbol_keys)} symbols...", flush=True)
    for symbol_key in symbol_keys:
        try:
            config = TICKERS[symbol_key]
            if not market_is_open(config["market"], datetime.now(IST)):
                print(f"  [{symbol_key}] market closed, skipping", flush=True)
                continue
            check_and_trade(symbol_key)
        except Exception as e:
            log_status(symbol_key, f"ERROR: {e}")


def run_slow_symbols():
    """NSE symbols â€” 5-minute candles, checked every 5 minutes."""
    keys = [k for k, v in TICKERS.items() if v["timeframe"] == "5m"]
    run_symbols(keys, "5m/NSE")


def run_fast_symbols():
    """Crypto/forex symbols â€” 1-minute candles, checked every 1 minute."""
    keys = [k for k, v in TICKERS.items() if v["timeframe"] == "1m"]
    run_symbols(keys, "1m/crypto+forex")


def get_dashboard_data():
    conn = sqlite3.connect(DB_PATH)
    trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC", conn)
    status_df = pd.read_sql_query("SELECT * FROM status_log ORDER BY id DESC LIMIT 40", conn)
    conn.close()

    closed = trades_df[trades_df["status"] == "CLOSED"] if not trades_df.empty else trades_df
    open_trades = trades_df[trades_df["status"] == "OPEN"] if not trades_df.empty else trades_df

    summary = {}
    for symbol_key, config in TICKERS.items():
        sym_closed = closed[closed["symbol"] == symbol_key] if not closed.empty else closed
        total = len(sym_closed)
        wins = len(sym_closed[sym_closed["pnl_rupees"] > 0]) if total else 0
        total_pnl = sym_closed["pnl_rupees"].sum() if total else 0
        summary[symbol_key] = {
            "market": config["market"],
            "timeframe": config["timeframe"],
            "total_trades": total,
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "total_pnl": round(total_pnl, 2),
        }

    return {
        "summary": summary,
        "open_trades": open_trades.to_dict("records"),
        "closed_trades": closed.to_dict("records"),
        "status_log": status_df.to_dict("records"),
        "last_updated": datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST"),
    }
