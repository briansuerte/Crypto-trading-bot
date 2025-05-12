from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class AlphaEdgeStrategy(IStrategy):
    INTERFACE_VERSION = 3

    minimal_roi = {
        "0": 0.05,
        "20": 0.03,
        "60": 0.01
    }

    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    timeframe = '1h'
    startup_candle_count: int = 50

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add indicators
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=26)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['rsi'] < 70) &
                (dataframe['volume'] > dataframe['volume_mean'])
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                (dataframe['rsi'] > 80)
            ),
            'sell'] = 1
        return dataframe