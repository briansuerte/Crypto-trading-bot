from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from datetime import datetime  # Critical fix for "name 'datetime' is not defined"
from freqtrade.persistence import Trade  # Required for 'Trade' type hint

class BTC2025Momentum(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False

    # Risk parameters
    stoploss = -0.15
    minimal_roi = {"0": 0.25, "12": 0.15, "24": 0.05}
    trailing_stop = True
    trailing_stop_positive = 0.08
    trailing_only_offset_is_reached = True
    use_custom_stoploss = True

    # Mandatory settings
    process_only_new_candles = True
    plot_config = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Core indicators
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema55'] = ta.EMA(dataframe, timeperiod=55)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volatility'] = dataframe['atr'] / dataframe['close']
        dataframe['volume_z'] = (dataframe['volume'] - dataframe['volume'].rolling(72).mean()) / dataframe['volume'].rolling(72).std()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema21'] > dataframe['ema55']) &
            (dataframe['rsi'] < 45) &
            (dataframe['volume_z'] > 1.5) &
            (dataframe['volatility'] < 0.03),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['ema21'] < dataframe['ema55']) |
            (dataframe['rsi'] > 65),
            'exit_long'] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        if last_candle['volatility'] > 0.04:
            return -0.25
        return -0.15