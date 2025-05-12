from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from functools import reduce

class OptimizedBTCStrategy(IStrategy):
    # 1. Strategy Configuration
    timeframe = '4h'
    stoploss = -0.12
    minimal_roi = {
        "0": 0.15,
        "24": 0.10,
        "48": 0.05
    }
    trailing_stop = True
    trailing_stop_positive = 0.06
    process_only_new_candles = True
    
    # Required even if empty
    plot_config = {}

    # 2. Indicator Calculation
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend Indicators
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        
        # Momentum
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        
        return dataframe

    # 3. Entry Signals
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe['ema20'] > dataframe['ema50'],
            dataframe['rsi'] < 48,
            dataframe['macd'] > dataframe['macd_signal']
        ]
        
        dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        return dataframe

    # 4. Exit Signals
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema20'] < dataframe['ema50']) |
            (dataframe['rsi'] > 65),
            'exit_long'] = 1
        return dataframe
