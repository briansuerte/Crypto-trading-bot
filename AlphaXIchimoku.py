# AlphaXIchimoku.py — Built for high compounding and adaptive market awareness

import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy
from freqtrade.vendor.qtpylib import indicators as qtpylib
from pandas import DataFrame


class AlphaXIchimoku(IStrategy):
    # === CONFIGURATION ===
    timeframe = '5m'
    startup_candle_count: int = 100
    process_only_new_candles = True
    use_custom_stoploss = True
    can_short = False  # Only long trades for now

    minimal_roi = {
        "0": 0.08,
        "30": 0.04,
        "60": 0.02,
        "120": 0
    }

    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03

    # === INDICATORS ===
    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Ichimoku base
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        df['tenkan'] = (high_9 + low_9) / 2

        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        df['kijun'] = (high_26 + low_26) / 2
        df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
        df['senkou_b'] = (df['high'].rolling(window=52).max() + df['low'].rolling(window=52).min()).shift(26) / 2

        df['ema_21'] = ta.EMA(df['close'], timeperiod=21)
        df['ema_50'] = ta.EMA(df['close'], timeperiod=50)
        df['rsi'] = ta.RSI(df['close'], timeperiod=14)
        df['adx'] = ta.ADX(df, timeperiod=14)
        df['atr'] = ta.ATR(df, timeperiod=14)
        df['volume_mean_slow'] = df['volume'].rolling(window=20).mean()
        df['volatility'] = df['close'].rolling(20).std()

        # Regime detection
        df['regime'] = np.select(
            [
                (df['adx'] > 25) & (df['volatility'] > df['volatility'].rolling(48).mean()),
                (df['adx'] < 18)
            ],
            [
                1,   # Bull
                -1   # Choppy
            ],
            default=0  # Bear
        )

        return df

    # === ENTRY CONDITIONS ===
    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Bull regime breakout entry
        bull_entry = (
            (df['regime'] == 1) &
            (df['close'] > df['ema_21']) &
            (df['tenkan'] > df['kijun']) &
            (df['volume'] > df['volume_mean_slow'] * 1.5) &
            (df['rsi'] > 55)
        )

        # Bear regime momentum entry
        bear_entry = (
            (df['regime'] == 0) &
            (df['close'] > df['ema_21']) &
            (df['rsi'] > 60) &
            (df['adx'] > 20)
        )

        # Choppy regime bounce entry
        choppy_entry = (
            (df['regime'] == -1) &
            (df['rsi'] < 35) &
            (qtpylib.crossed_above(df['rsi'], 35)) &
            (df['close'] > df['tenkan']) &
            (df['volume'] > df['volume_mean_slow'])
        )

        conditions.append(bull_entry | bear_entry | choppy_entry)

        df.loc[np.all(conditions, axis=0), 'enter_long'] = 1
        return df

    # === EXIT CONDITIONS ===
    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        exit_signal = (
            (df['rsi'] < 48) |
            (df['close'] < df['ema_21']) |
            (df['tenkan'] < df['kijun'])
        )
        df.loc[exit_signal, 'exit_long'] = 1
        return df

    # === CUSTOM STOPLOSS ===
    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        if current_profit < -0.02:
            return 0.01  # Exit fast if trade goes wrong
        return 1  # Let trailing stop handle the rest