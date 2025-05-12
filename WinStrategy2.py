from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import numpy as np
import talib.abstract as ta

class WinStrategy2(IStrategy):
    # Optimal timeframe for the strategy
    timeframe = '1h'

    # Strategy parameters
    stop_loss_percentage = 0.02
    take_profit_percentage = 0.04
    trailing_stop_percentage = 0.03
    risk_per_trade = 0.01
    ema_period = 50
    macd_short_period = 12
    macd_long_period = 26
    macd_signal_period = 9
    rsi_period = 14

    # Stoploss and trailing config
    minimal_roi = {"0": take_profit_percentage}
    stoploss = -stop_loss_percentage
    trailing_stop = True
    trailing_stop_positive = trailing_stop_percentage
    trailing_stop_positive_offset = trailing_stop_percentage
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA
        dataframe['ema'] = ta.EMA(dataframe, timeperiod=self.ema_period)
        # MACD
        macd = ta.MACD(dataframe, fastperiod=self.macd_short_period, slowperiod=self.macd_long_period, signalperiod=self.macd_signal_period)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema']) &
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['rsi'] < 70)
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['ema']) &
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['rsi'] > 30)
            ),
            'sell'] = 1
        return dataframe
