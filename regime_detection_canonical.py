import ccxt
import pandas as pd
import ta
from datetime import datetime

# Setup exchange
exchange = ccxt.binance()
symbol = 'BTC/USDT'
timeframe = '1d'

# Time ranges for your tested strategy
time_ranges = {
    'Bull (Q4 2023)': ('2023-10-01T00:00:00Z', '2023-12-31T23:59:59Z'),
    'Bear (Aug-Sep 2023)': ('2023-08-01T00:00:00Z', '2023-09-30T23:59:59Z'),
    'Sideways (Jan-Feb 2024)': ('2024-01-01T00:00:00Z', '2024-02-29T23:59:59Z')
}

def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    all_data = []
    since_ms = exchange.parse8601(since)
    while True:
        data = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        if not data:
            break
        all_data += data
        since_ms = data[-1][0] + 1
        if len(data) < limit:
            break
    return all_data

def prepare_df(data):
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def detect_regimes(df):
    # Calculate indicators
    df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
    df['sma_50'] = df['close'].rolling(window=50).mean()

    # Drop rows where indicators are NaN
    df = df.dropna(subset=['adx', 'sma_50'])

    # Apply regime logic
    def classify(row):
        if row['adx'] > 25:
            if row['close'] > row['sma_50']:
                return 'bull'
            else:
                return 'bear'
        else:
            return 'sideways'

    df['regime'] = df.apply(classify, axis=1)
    return df

def summarize_regime_distribution(df, start_iso, end_iso):
    mask = (df.index >= start_iso) & (df.index <= end_iso)
    filtered = df.loc[mask]
    distribution = filtered['regime'].value_counts(normalize=True) * 100
    return distribution

def main():
    for period_name, (start_iso, end_iso) in time_ranges.items():
        print(f"Fetching data for {period_name} ({start_iso} to {end_iso})...")
        data = fetch_ohlcv(symbol, timeframe, start_iso)
        df = prepare_df(data)
        df = detect_regimes(df)
        dist = summarize_regime_distribution(df, start_iso, end_iso)
        print(f"Regime distribution for {symbol} from {start_iso} to {end_iso}:")
        print(dist)
        print()

if __name__ == '__main__':
    main()
