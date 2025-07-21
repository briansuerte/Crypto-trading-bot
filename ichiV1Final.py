from freqtrade.strategy import IStrategy, Decimal  
import pandas as pd  
import talib.abstract as ta  

class ichiV1Final(IStrategy):  
    INTERFACE_VERSION = 3  
    timeframe = '15m'  
    minimal_roi = {"0": 0.15, "20": 0.035, "60": 0.01, "120": 0}  
    stoploss = -0.10  
    trailing_stop = True  
    trailing_stop_positive = 0.05  
    trailing_stop_positive_offset = 0.1  
    startup_candle_count = 100  # Required for EMA stability [citation:9]  

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:  
        # Ichimoku Cloud  
        dataframe['tenkan'] = ta.EMA(dataframe, timeperiod=9)  
        dataframe['kijun'] = ta.EMA(dataframe, timeperiod=26)  
        dataframe['senkou_a'] = (dataframe['tenkan'] + dataframe['kijun']) / 2  
        # RSI Filter  
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)  
        return dataframe  

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:  
        dataframe.loc[  
            (dataframe['close'] > dataframe['senkou_a']) &  # Price above cloud  
            (dataframe['rsi'] < 45) &  # Oversold RSI  
            (dataframe['volume'] > 0),  # Liquidity check [citation:9]  
            'enter_long'] = 1  
        return dataframe