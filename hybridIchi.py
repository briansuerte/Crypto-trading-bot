from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
from functools import reduce
import technical.indicators as ftt  # your ichimoku helper


class HybridIchi(IStrategy):
    # Strategy parameters
    timeframe = '5m'
    startup_candle_count = 96
    process_only_new_candles = False

    # ROI table (adjust as needed)
    minimal_roi = {
        "0": 0.05,
        "10": 0.03,
        "30": 0.015,
        "60": 0
    }

    stoploss = -0.275

    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Buy hyperspace parameters (you can tune these)
    buy_params = {
        "buy_trend_above_senkou_level": 3,
        "buy_trend_bullish_level": 6,
        "buy_min_fan_magnitude_gain": 1.005,
        "buy_fan_magnitude_shift_value": 3,
        "rsi_buy_threshold": 50,
        "relative_strength_threshold": 0.7,
    }

    # Sell parameters
    sell_params = {
        "sell_trend_indicator": "trend_close_2h",
    }

    # Indicators and regime detection
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Heikin Ashi candles for smoothing
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['open'] = heikinashi['open']
        dataframe['high'] = heikinashi['high']
        dataframe['low'] = heikinashi['low']

        # EMAs for multiple timeframes (for trend & regime detection)
        dataframe['trend_close_5m'] = dataframe['close']
        dataframe['trend_close_15m'] = ta.EMA(dataframe['close'], timeperiod=3)
        dataframe['trend_close_30m'] = ta.EMA(dataframe['close'], timeperiod=6)
        dataframe['trend_close_1h'] = ta.EMA(dataframe['close'], timeperiod=12)
        dataframe['trend_close_2h'] = ta.EMA(dataframe['close'], timeperiod=24)
        dataframe['trend_close_4h'] = ta.EMA(dataframe['close'], timeperiod=48)
        dataframe['trend_close_6h'] = ta.EMA(dataframe['close'], timeperiod=72)
        dataframe['trend_close_8h'] = ta.EMA(dataframe['close'], timeperiod=96)

        dataframe['trend_open_5m'] = ta.EMA(dataframe['open'], timeperiod=3)
        dataframe['trend_open_15m'] = ta.EMA(dataframe['open'], timeperiod=9)
        dataframe['trend_open_30m'] = ta.EMA(dataframe['open'], timeperiod=18)
        dataframe['trend_open_1h'] = ta.EMA(dataframe['open'], timeperiod=36)
        dataframe['trend_open_2h'] = ta.EMA(dataframe['open'], timeperiod=72)
        dataframe['trend_open_4h'] = ta.EMA(dataframe['open'], timeperiod=144)
        dataframe['trend_open_6h'] = ta.EMA(dataframe['open'], timeperiod=216)
        dataframe['trend_open_8h'] = ta.EMA(dataframe['open'], timeperiod=288)

        # Fan magnitude for trend strength
        dataframe['fan_magnitude'] = dataframe['trend_close_1h'] / dataframe['trend_close_8h']
        dataframe['fan_magnitude_gain'] = dataframe['fan_magnitude'] / dataframe['fan_magnitude'].shift(1)

        # Ichimoku cloud lines
        ichimoku = ftt.ichimoku(
            dataframe,
            conversion_line_period=20,
            base_line_periods=60,
            laggin_span=120,
            displacement=30,
        )
        dataframe['chikou_span'] = ichimoku['chikou_span']
        dataframe['tenkan_sen'] = ichimoku['tenkan_sen']
        dataframe['kijun_sen'] = ichimoku['kijun_sen']
        dataframe['senkou_a'] = ichimoku['senkou_span_a']
        dataframe['senkou_b'] = ichimoku['senkou_span_b']

        # RSI for momentum filtering
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)

        # ATR for volatility context (optional for future use)
        dataframe['atr'] = ta.ATR(dataframe)

        # Regime detection:
        ema50 = ta.EMA(dataframe['close'], timeperiod=50)
        ema200 = ta.EMA(dataframe['close'], timeperiod=200)
        adx = ta.ADX(dataframe)

        dataframe['bull_regime'] = (ema50 > ema200) & (adx > 25)
        dataframe['choppy_regime'] = adx < 20
        dataframe['regime'] = np.select(
            [dataframe['bull_regime'], dataframe['choppy_regime']],
            ['BULL', 'CHOPPY'],
            default='GENERAL',
        )

        # Relative strength (24h % change approx 288 candles of 5m = 24h)
        dataframe['24h_pct'] = dataframe['close'] / dataframe['close'].shift(288) - 1

        # We rank the pair's strength and mark if it's top 30%
        # Note: This works if you do it in your backtesting/live environment where multiple pairs dataframes are merged and ranked
        # Here we just prepare the column
        dataframe['relative_strength_pass'] = dataframe['24h_pct'] > dataframe['24h_pct'].quantile(self.buy_params['relative_strength_threshold'])

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Filter out pairs without relative strength
        conditions.append(dataframe['relative_strength_pass'])

        # Basic trend checks — cloud & multi-timeframe EMA support
        regime = dataframe['regime'].iloc[-1]

        # Buy conditions per regime
        if regime == 'BULL':
            # Require more timeframes above cloud and fan magnitude higher threshold
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_b'])
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_b'])
            conditions.append(dataframe['trend_close_30m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_30m'] > dataframe['senkou_b'])
            conditions.append(dataframe['fan_magnitude_gain'] >= self.buy_params['buy_min_fan_magnitude_gain'])
            conditions.append(dataframe['fan_magnitude'] > 1)
            conditions.append(dataframe['rsi'] > self.buy_params['rsi_buy_threshold'])
        elif regime == 'CHOPPY':
            # More lenient buy, fewer cloud timeframe checks, lower fan threshold
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_b'])
            conditions.append(dataframe['fan_magnitude_gain'] >= 1.002)
            conditions.append(dataframe['fan_magnitude'] > 1)
        else:
            # General regime, medium strictness
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_5m'] > dataframe['senkou_b'])
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_a'])
            conditions.append(dataframe['trend_close_15m'] > dataframe['senkou_b'])
            conditions.append(dataframe['fan_magnitude_gain'] >= 1.003)
            conditions.append(dataframe['fan_magnitude'] > 1)

        # Fan magnitude shift validation to catch upward momentum
        for x in range(self.buy_params['buy_fan_magnitude_shift_value']):
            conditions.append(dataframe['fan_magnitude'].shift(x + 1) < dataframe['fan_magnitude'])

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        # Basic sell on EMA cross below trend indicator (like your old ichiV1)
        conditions.append(qtpylib.crossed_below(dataframe['trend_close_5m'], dataframe[self.sell_params['sell_trend_indicator']]))

        # Optionally add mid-wave take profit exit for bullish regime
        # This can be implemented in a callback or external monitoring system to send alerts
        # Here is a placeholder comment for that logic

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'sell'] = 1

        return dataframe