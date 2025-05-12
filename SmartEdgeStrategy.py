from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SmartEdgeStrategy(IStrategy):
    # Minimal ROI designed for long-term performance
    minimal_roi = {
        "0": 0.05
    }

    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    timeframe = '5m'
    startup_candle_count: int = 50
    use_custom_stoploss = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=26)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['rsi'] < 70)
            ),
            'buy'
        ] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema_fast'] < dataframe['ema_slow']) |
                (dataframe['rsi'] > 80)
            ),
            'sell'
        ] = 1
        return dataframe