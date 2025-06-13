# ichi_allweather_15m.py
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import pandas as pd
import numpy as np
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime

class ichi_allweather_15m(IStrategy):
    # Optimized parameters
    buy_params = {
        "bull_rsi_entry": 48,
        "bear_rsi_entry": 28,
        "choppy_atr_entry": 0.018,
        "volume_multiplier": 1.3,
        "cloud_breakout_strength": 2
    }
    sell_params = {
        "bull_rsi_exit": 65,
        "bear_rsi_exit": 72,
        "choppy_profit_target": 0.012,
        "trailing_stop_activation": 0.03,
        "trailing_stop_distance": 0.008
    }
    
    minimal_roi = {"0": 0.20, "10": 0.12, "30": 0.05, "60": 0}
    stoploss = -0.022
    timeframe = '15m'
    startup_candle_count = 168

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Market regime detection
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['atr_pct'] = ta.ATR(dataframe, timeperiod=14) / dataframe['close'] * 100
        
        # Classify market regime
        bull = (dataframe['ema_50'] > dataframe['ema_200']) & (dataframe['adx'] > 25)
        bear = (dataframe['ema_50'] < dataframe['ema_200']) & (dataframe['adx'] > 25)
        choppy = dataframe['adx'] < 20
        
        dataframe['market_regime'] = np.select(
            [bull, bear, choppy],
            [1, 2, 3],
            default=1
        )
        
        # Ichimoku Cloud
        high_9 = dataframe['high'].rolling(9).max()
        low_9 = dataframe['low'].rolling(9).min()
        dataframe['tenkan_sen'] = (high_9 + low_9) / 2
        
        high_26 = dataframe['high'].rolling(26).max()
        low_26 = dataframe['low'].rolling(26).min()
        dataframe['kijun_sen'] = (high_26 + low_26) / 2
        
        high_52 = dataframe['high'].rolling(52).max()
        low_52 = dataframe['low'].rolling(52).min()
        dataframe['senkou_b'] = (high_52 + low_52) / 2
        dataframe['senkou_a'] = ((dataframe['tenkan_sen'] + dataframe['kijun_sen']) / 2)
        
        # Shift clouds forward
        dataframe['senkou_a'] = dataframe['senkou_a'].shift(26)
        dataframe['senkou_b'] = dataframe['senkou_b'].shift(26)
        
        # Volume spike detection
        dataframe['volume_ma'] = ta.SMA(dataframe['volume'], 20)
        dataframe['volume_spike'] = dataframe['volume'] > self.buy_params['volume_multiplier'] * dataframe['volume_ma']
        
        return dataframe

    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        p = self.buy_params
        
        # Bull market conditions
        bull_cond = (
            (dataframe['market_regime'] == 1) &
            (dataframe['close'] > dataframe['senkou_a']) &
            (dataframe['close'] > dataframe['senkou_b']) &
            (dataframe['rsi'] > p['bull_rsi_entry']) &
            (dataframe['rsi'] < 65) &
            (dataframe['volume_spike'])
        )
        
        # Bear market conditions
        bear_cond = (
            (dataframe['market_regime'] == 2) &
            (dataframe['rsi'] < p['bear_rsi_entry']) &
            (dataframe['close'] < dataframe['senkou_a']) &
            (qtpylib.crossed_above(dataframe['close'], dataframe['kijun_sen']))
        )
        
        # Choppy market conditions
        choppy_cond = (
            (dataframe['market_regime'] == 3) &
            (dataframe['atr_pct'] > p['choppy_atr_entry']) &
            (dataframe['volume_spike']) &
            (qtpylib.crossed_above(dataframe['close'], dataframe['senkou_a'])) &
            (dataframe['close'] > dataframe['ema_50'])
        )
        
        # Set buy signals
        dataframe.loc[bull_cond, 'buy'] = 1
        dataframe.loc[bear_cond, 'buy'] = 1
        dataframe.loc[choppy_cond, 'buy'] = 1
        
        return dataframe

    def populate_sell_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        p = self.sell_params
        
        # Bull market exit
        bull_exit = (dataframe['market_regime'] == 1) & (dataframe['rsi'] > p['bull_rsi_exit'])
        
        # Bear market exit
        bear_exit = (dataframe['market_regime'] == 2) & (dataframe['close'] > dataframe['senkou_a'] * 1.018)
        
        # Choppy market exit
        choppy_exit = (
            (dataframe['market_regime'] == 3) &
            (dataframe["close"] < dataframe["close"].shift(1) * (1 - p['trailing_stop_distance']))
        )
        
        # Set sell signals
        dataframe.loc[bull_exit, 'sell'] = 1
        dataframe.loc[bear_exit, 'sell'] = 1
        dataframe.loc[choppy_exit, 'sell'] = 1
        
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, 
                        current_rate: float, current_profit: float, **kwargs) -> float:
        if current_profit > self.sell_params['trailing_stop_activation']:
            return current_profit - self.sell_params['trailing_stop_distance']
        return self.stoploss