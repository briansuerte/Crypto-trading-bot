from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class BTC2025Momentum(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False

    # Risk parameters (aggressive but safe)
    stoploss = -0.15
    trailing_stop = True
    trailing_stop_positive = 0.08
    trailing_only_offset_is_reached = True
    use_custom_stoploss = True
    minimal_roi = {
        "0": 0.25,    # 25% profit for immediate exit
        "12": 0.15,   # After 12 candles: 15%
        "24": 0.05    # After 24 candles: 5%
    }

    # Required for modern Freqtrade
    process_only_new_candles = True
    use_exit_signal = True
    ignore_buying_expired_candle_after = 60
    plot_config = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Core indicators
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema55'] = ta.EMA(dataframe, timeperiod=55)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Modern volatility filter (ATR-based)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volatility'] = dataframe['atr'] / dataframe['close']
        
        # AI/Institutional flow detection (requires 2025 data patterns)
        dataframe['volume_z'] = (dataframe['volume'] - dataframe['volume'].rolling(72).mean()) / dataframe['volume'].rolling(72).std()
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bullish momentum criteria
        dataframe.loc[
            (dataframe['ema21'] > dataframe['ema55']) &
            (dataframe['rsi'] < 45) &
            (dataframe['volume_z'] > 1.5) &  # Volume spike detection
            (dataframe['volatility'] < 0.03),  # Avoid high volatility periods
            'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Dynamic exit conditions
        dataframe.loc[
            (dataframe['ema21'] < dataframe['ema55']) |
            (dataframe['rsi'] > 65),
            'exit_long'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        # Dynamic stoploss based on volatility
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        if last_candle['volatility'] > 0.04:
            return -0.25  # Wider stop during high volatility
        return -0.15
