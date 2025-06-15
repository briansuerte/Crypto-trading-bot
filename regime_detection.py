import ccxt
import pandas as pd
import talib

def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    exchange = ccxt.binance()
    data = []
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not batch:
            break
        data.extend(batch)
        since = batch[-1][0] + 1
        if len(batch) < limit:
            break
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    return df

def add_indicators(df):
    df['ema200'] = talib.EMA(df['close'], timeperiod=200)
    df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    return df

def classify_regime(row):
    if row['adx'] <= 25:
        return 'sideways'
    elif row['adx'] > 25 and row['close'] > row['ema200'] and row['rsi'] > 55:
        return 'bull'
    elif row['adx'] > 25 and row['close'] < row['ema200'] and row['rsi'] < 45:
        return 'bear'
    else:
        return 'sideways'

def analyze_period(symbol, start_str, end_str):
    timeframe = '1h'
    start = int(pd.Timestamp(start_str, tz='UTC').timestamp() * 1000)
    end = int(pd.Timestamp(end_str, tz='UTC').timestamp() * 1000)
    df = fetch_ohlcv(symbol, timeframe, start)
    df = df[(df['timestamp'] >= pd.Timestamp(start_str, tz='UTC')) & (df['timestamp'] <= pd.Timestamp(end_str, tz='UTC'))]
    df = add_indicators(df)
    df['regime'] = df.apply(classify_regime, axis=1)
    counts = df['regime'].value_counts(normalize=True) * 100
    print(f"Regime distribution for {symbol} from {start_str} to {end_str}:")
    print(counts.to_string())
    print()

if __name__ == "__main__":
    periods = {
        "Bull (Q4 2023)": ("2023-10-01T00:00:00Z", "2023-12-31T23:59:59Z"),
        "Bear (Aug-Sep 2023)": ("2023-08-01T00:00:00Z", "2023-09-30T23:59:59Z"),
        "Sideways (Jan-Feb 2024)": ("2024-01-01T00:00:00Z", "2024-02-29T23:59:59Z")
    }
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    for period_name, (start, end) in periods.items():
        print(f"--- {period_name} ---")
        for symbol in symbols:
            analyze_period(symbol, start, end)
