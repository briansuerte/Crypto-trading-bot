from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class BTC2025Momentum(IStrategy):  # Class name MATCHES filename
    INTERFACE_VERSION = 3
    timeframe = '1h'

    # Mandatory settings
    stoploss = -0.15
    minimal_roi = {"0": 0.25, "12": 0.15, "24": 0.05}
    trailing_stop = True
    process_only_new_candles = True
    plot_config = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema55'] = ta.EMA(dataframe, timeperiod=55)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema21'] > dataframe['ema55']) & 
            (dataframe['rsi'] < 45),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema21'] < dataframe['ema55']),
            'exit_long'] = 1
        return dataframe