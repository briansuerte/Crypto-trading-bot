from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class AdvancedBTCStrategy(IStrategy):
    # 1. Strategy Configuration
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    # 2. Risk Parameters
    stoploss = -0.12
    minimal_roi = {
        "0": 0.2,    # 20% profit for immediate exit
        "6": 0.1,    # 10% after 6 candles
        "12": 0.05   # 5% after 12 candles
    }
    trailing_stop = True
    trailing_stop_positive = 0.08
    trailing_only_offset_is_reached = True
    use_custom_stoploss = True
    
    # 3. Mandatory Settings
    process_only_new_candles = True
    plot_config = {}

    # 4. Indicators (All-in-One)
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend Indicators
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema55'] = ta.EMA(dataframe, timeperiod=55)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Momentum
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        
        # Volume Analysis
        dataframe['volume_ma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        
        # Volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    # 5. Entry Logic (Multi-Condition)
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            # Trend Filter: EMA21 > EMA55 > EMA200 (bullish stack)
            (dataframe['ema21'] > dataframe['ema55']) &
            (dataframe['ema55'] > dataframe['ema200']) &
            
            # Momentum Filter: RSI < 45 & MACD crossover
            (dataframe['rsi'] < 45) &
            (qtpylib.crossed_above(dataframe['macd'], dataframe['macd_signal'])) &
            
            # Volume Filter: Current volume > 1.3x 20-period average
            (dataframe['volume_ratio'] > 1.3),
            'enter_long'] = 1
        return dataframe

    # 6. Exit Logic
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            # Trend Reversal: EMA21 crosses below EMA55
            (qtpylib.crossed_below(dataframe['ema21'], dataframe['ema55'])) |
            
            # Profit Protection: RSI overbought
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        return dataframe

    # 7. Dynamic Stoploss based on ATR
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # Tighten stoploss if volatility is low
        if last_candle['atr'] < 0.02 * current_rate:
            return -0.08  # 8% stoploss
        return self.stoploss  # Default 12%
