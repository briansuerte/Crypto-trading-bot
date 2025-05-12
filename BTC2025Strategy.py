from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class BTC2025Strategy(IStrategy):
    timeframe = '4h'
    stoploss = -0.1
    minimal_roi = {"0": 0.15, "24": 0.1, "48": 0.05}
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend Indicators
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe)
        
        # Momentum
        dataframe['rsi'] = ta.RSI(dataframe)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['signal'] = macd['signal']
        
        # Volume Analysis
        dataframe['volume_ma20'] = ta.SMA(dataframe['volume'], 20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema50'] > dataframe['ema200']) &
            (dataframe['adx'] > 25) &
            (dataframe['rsi'] < 40) &
            (dataframe['macd'] > dataframe['signal']) &
            (dataframe['volume'] > 1.2 * dataframe['volume_ma20']),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema50'] < dataframe['ema200']) |
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        return dataframe