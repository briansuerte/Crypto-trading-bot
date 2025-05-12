from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class BTC2025Strategy(IStrategy):
    # Mandatory settings
    timeframe = '4h'
    stoploss = -0.1
    minimal_roi = {
        "0": 0.15,
        "24": 0.1,   # 24 candles (4h * 24 = 4 days)
        "48": 0.05   # 8 days
    }
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_only_offset_is_reached = True

    # Fix 1: Add required plot configuration (empty for minimal setup)
    plot_config = {}

    # Fix 2: Correct MACD syntax + ADX parameters
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        
        # Fix 3: Properly unpack MACD values
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']
        
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['volume_ma20'] = ta.SMA(dataframe['volume'], timeperiod=20)
        return dataframe

    # Fix 4: Use explicit column assignment for signals
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema50'] > dataframe['ema200']) &
            (dataframe['adx'] > 25) &
            (dataframe['rsi'] < 40) &
            (dataframe['macd'] > dataframe['macd_signal']) &
            (dataframe['volume'] > 1.2 * dataframe['volume_ma20']),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema50'] < dataframe['ema200']) |
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        return dataframe