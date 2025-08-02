
# AlphaXScalperV2.py
# Rebuilt on 2025-08-02 to fix poor performance and apply dynamic exits

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class AlphaXScalperV2(IStrategy):
    timeframe = '5m'
    minimal_roi = { "0": 0.01 }
    stoploss = -0.02  # Will override with dynamic SL
    trailing_stop = False
    use_custom_stoploss = True
    process_only_new_candles = True
    startup_candle_count = 50
    max_open_trades = 5

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Technical Indicators
        dataframe['ema20'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['ema50'] = ta.EMA(dataframe['close'], timeperiod=50)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=4)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=30).mean()
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Basic checks
        conditions.append(dataframe['volume'] > 0)
        conditions.append(dataframe['volume'] > dataframe['volume_mean_slow'])

        # Momentum conditions
        conditions.append(dataframe['rsi'] < 70)
        conditions.append(dataframe['close'] > dataframe['ema20'])
        conditions.append(dataframe['ema20'] > dataframe['ema50'])

        # Price breakout (simple pattern)
        conditions.append(dataframe['close'] > dataframe['close'].shift(1) * 1.003)

        if conditions:
            dataframe.loc[np.all(conditions, axis=0), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # No static sell condition: we exit using dynamic SL/TP or timeout
        dataframe['sell'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        # Get ATR-based stoploss
        atr = self.dp.get_indicator(pair, 'atr', self.timeframe)
        if atr is None:
            return 1  # don't exit

        try:
            trade_open_index = atr.index.get_loc(trade.open_date_utc, method='nearest')
            trade_atr = atr.iloc[trade_open_index]
        except Exception:
            trade_atr = 0.01

        # Custom SL: 1x ATR from entry
        sl_price = trade.open_rate - trade_atr
        if current_rate < sl_price:
            return 0.99  # trigger immediate exit
        return 1

    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        atr = self.dp.get_indicator(pair, 'atr', self.timeframe)
        if atr is None:
            return None

        try:
            trade_open_index = atr.index.get_loc(trade.open_date_utc, method='nearest')
            trade_atr = atr.iloc[trade_open_index]
        except Exception:
            trade_atr = 0.01

        # Dynamic TP: exit at 1.5x ATR profit
        tp_price = trade.open_rate + 1.5 * trade_atr
        sl_price = trade.open_rate - 1.0 * trade_atr

        if current_rate >= tp_price:
            return 'atr_tp', 1
        elif current_rate <= sl_price:
            return 'atr_sl', 1
        elif trade.duration > 45:
            return 'timeout', 1
        return None
