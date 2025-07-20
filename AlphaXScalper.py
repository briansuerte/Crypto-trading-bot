from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class AlphaXScalper(IStrategy):
    INTERFACE_VERSION = 3

    # Strategy parameters
    timeframe = '5m'
    startup_candle_count: int = 50
    can_short: bool = False

    # Risk management
    minimal_roi = {
        "0": 0.04,
        "20": 0.02,
        "40": 0
    }

    stoploss = -0.15
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03

    use_custom_stoploss = False
    process_only_new_candles = True
    ignore_buying_expired_candles = True

    max_open_trades = 5

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        df['rsi'] = ta.RSI(df, timeperiod=14)
        df['ema_fast'] = ta.EMA(df['close'], timeperiod=5)
        df['ema_slow'] = ta.EMA(df['close'], timeperiod=20)
        df['adx'] = ta.ADX(df)

        df['price_change'] = df['close'].pct_change(3) * 100  # momentum burst

        return df

    def populate_buy_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (
                (df['ema_fast'] > df['ema_slow']) &
                (df['rsi'] > 55) &
                (df['adx'] > 20) &
                (df['price_change'] > 1)
            ),
            'buy'] = 1
        return df

    def populate_sell_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (
                (df['rsi'] > 75) |
                (df['price_change'] < -2)
            ),
            'sell'] = 1
        return df