from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
from functools import reduce
from technical.indicators import ichimoku
import logging
from datetime import datetime

class AdaptiveMarketSpecialist(IStrategy):
    # Strategy configuration
    timeframe = '5m'
    startup_candle_count = 288  # 24 hours of 5m candles
    process_only_new_candles = True
    use_custom_stoploss = True

    # Dynamic ROI table for different market conditions
    minimal_roi = {
        "0": 0.02,   # 2% immediate profit
        "30": 0.015, # 1.5% additional after 30 candles
        "60": 0.01,  # 1% additional after 60 candles
        "120": 0.005 # 0.5% additional after 120 candles
    }

    # Strategy parameters optimized for all market conditions
    buy_params = {
        # Choppy market params
        "choppy_rsi_min": 45,
        "choppy_rsi_max": 65,
        "choppy_volume_mult": 2.5,
        "choppy_consolidation": 14,
        
        # Bull market params
        "bull_rsi_min": 40,
        "bull_rsi_max": 75,
        "bull_volume_mult": 1.8,
        "bull_pullback_pct": -0.03,
        
        # Common params
        "relative_strength": 1.005
    }

    sell_params = {
        "choppy_trailing_stop": 0.008,
        "bull_trailing_stop": 0.015,
        "choppy_profit_threshold": 0.015,
        "bull_profit_threshold": 0.03,
        "max_hold_period": 240
    }

    # Trailing stop configuration
    trailing_stop = True
    trailing_only_offset_is_reached = True

    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.market_regime = "CHOPPY"  # Default
        self.last_regime_update = None

    def determine_market_regime(self, current_time: datetime) -> str:
        """Enhanced regime detection for all market types"""
        try:
            btc_df = self.dp.get_pair_dataframe("BTC/USDT", self.timeframe)
            if len(btc_df) < 100:
                return self.market_regime
                
            close = btc_df['close']
            high = btc_df['high']
            low = btc_df['low']
            
            # Calculate indicators
            ema25 = ta.EMA(close, 25).iloc[-1]
            ema100 = ta.EMA(close, 100).iloc[-1]
            current_close = close.iloc[-1]
            adx = ta.ADX(high, low, close, 14).iloc[-1]
            atr_pct = ta.ATR(high, low, close, 14).iloc[-1] / current_close
            
            # Bull market detection
            bull_conditions = (
                current_close > ema25 > ema100 and
                adx > 25 and
                atr_pct > 0.01
            )
            
            # Choppy market detection
            choppy_conditions = (
                adx < 20 and
                abs(ema25 - ema100)/current_close < 0.03 and
                atr_pct < 0.008
            )
            
            # Bear market detection
            bear_conditions = (
                current_close < ema25 < ema100 and
                adx > 28
            )
            
            if bull_conditions:
                return "BULL"
            elif choppy_conditions:
                return "CHOPPY"
            elif bear_conditions:
                return "BEAR"
            return "NEUTRAL"
                
        except Exception as e:
            logging.error(f"Regime error: {e}")
            return self.market_regime

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs) -> float:
        """Regime-specific stop loss"""
        # Dynamic trailing stops
        if self.market_regime == "BULL":
            if current_profit > self.sell_params["bull_trailing_stop"]:
                return -0.02  # 2% trailing in bulls
            return -0.04  # 4% initial stop
            
        elif self.market_regime == "CHOPPY":
            if current_profit > self.sell_params["choppy_trailing_stop"]:
                return -0.01  # 1% trailing in choppy
            return -0.03  # 3% initial stop
            
        return -0.05  # 5% stop for bears/neutral

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Update market regime
        current_time = self.dp.get_current_time() if hasattr(self.dp, 'get_current_time') else datetime.utcnow()
        self.market_regime = self.determine_market_regime(current_time)
        dataframe['global_regime'] = self.market_regime
        
        # Heikin Ashi smoothing
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['close_ha'] = heikinashi['close']
        dataframe['high_ha'] = heikinashi['high']
        dataframe['low_ha'] = heikinashi['low']
        
        # Support/Resistance levels
        dataframe['support'] = ta.MIN(dataframe['low'], timeperiod=20)
        dataframe['resistance'] = ta.MAX(dataframe['high'], timeperiod=20)
        
        # Consolidation detection
        dataframe['range'] = dataframe['high'] - dataframe['low']
        dataframe['avg_range'] = dataframe['range'].rolling(window=20).mean()
        dataframe['consolidating'] = dataframe['range'] < dataframe['avg_range'] * 0.7

        # Ichimoku Cloud
        ichi = ichimoku(dataframe, conversion_line_period=20, base_line_periods=60, 
                       laggin_span=120, displacement=30)
        for key in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b']:
            dataframe[key] = ichi[key]

        # Momentum indicators
        dataframe['rsi'] = ta.RSI(dataframe['close_ha'], timeperiod=14)
        dataframe['mfi'] = ta.MFI(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        
        # Pullback detection for bull markets
        dataframe['pullback'] = dataframe['close_ha'].pct_change(periods=8)
        
        # Relative strength to BTC
        btc_close = self.dp.get_pair_dataframe("BTC/USDT", self.timeframe)['close']
        if not btc_close.empty:
            btc_close = btc_close.reindex(dataframe.index, method='ffill')
            dataframe['btc_relative'] = dataframe['close_ha'] / btc_close
        else:
            dataframe['btc_relative'] = 1.0

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        conditions = []
        debug_info = [f"Regime: {self.market_regime}"]
        
        # COMMON CONDITIONS (all regimes)
        # Relative strength
        rel_strength = dataframe['btc_relative'] > self.buy_params['relative_strength']
        conditions.append(rel_strength)
        debug_info.append(f"Rel Strength: {dataframe['btc_relative'].iloc[-1]:.4f}")
        
        # Volume above average
        vol_ma = dataframe['volume'].rolling(window=20).mean()
        
        # REGIME-SPECIFIC CONDITIONS
        if self.market_regime == "CHOPPY":
            # Choppy market strategy
            conditions.append(dataframe['consolidating'].rolling(
                self.buy_params['choppy_consolidation']).min().astype(bool))
            conditions.append(dataframe['close_ha'] < dataframe['support'] + dataframe['atr'])
            
            vol_cond = dataframe['volume'] > vol_ma * self.buy_params['choppy_volume_mult']
            conditions.append(vol_cond)
            
            rsi_cond = (dataframe['rsi'] > self.buy_params['choppy_rsi_min']) & \
                       (dataframe['rsi'] < self.buy_params['choppy_rsi_max'])
            conditions.append(rsi_cond)
            
            debug_info.extend([
                f"Consolidating: {conditions[-3].iloc[-1]}",
                f"Near Support: {conditions[-2].iloc[-1]}",
                f"Volume: {vol_cond.iloc[-1]} ({dataframe['volume'].iloc[-1]/vol_ma.iloc[-1]:.1f}x)",
                f"RSI: {dataframe['rsi'].iloc[-1]:.1f}"
            ])
            
        elif self.market_regime == "BULL":
            # Bull market strategy
            conditions.append(dataframe['close_ha'] > dataframe['senkou_span_a'])
            conditions.append(dataframe['close_ha'] > dataframe['senkou_span_b'])
            
            # Pullback entry
            pullback_cond = dataframe['pullback'] < self.buy_params['bull_pullback_pct']
            conditions.append(pullback_cond)
            
            vol_cond = dataframe['volume'] > vol_ma * self.buy_params['bull_volume_mult']
            conditions.append(vol_cond)
            
            rsi_cond = (dataframe['rsi'] > self.buy_params['bull_rsi_min']) & \
                       (dataframe['rsi'] < self.buy_params['bull_rsi_max'])
            conditions.append(rsi_cond)
            
            debug_info.extend([
                f"Above Cloud: {conditions[-4].iloc[-1]}",
                f"Pullback: {pullback_cond.iloc[-1]*100:.1f}%",
                f"Volume: {vol_cond.iloc[-1]} ({dataframe['volume'].iloc[-1]/vol_ma.iloc[-1]:.1f}x)",
                f"RSI: {dataframe['rsi'].iloc[-1]:.1f}"
            ])
            
        else:  # BEAR/NEUTRAL
            # Original bear strategy
            conditions.append(dataframe['consolidating'].rolling(12).min().astype(bool))
            conditions.append(dataframe['close_ha'] < dataframe['support'] + dataframe['atr'] * 1.5)
            conditions.append(dataframe['volume'] > vol_ma * 2.2)
            conditions.append(dataframe['rsi'] > 38)
            
        # Apply conditions
        if conditions:
            buy_signal = reduce(lambda x, y: x & y, conditions)
            dataframe.loc[buy_signal, 'buy'] = 1
            
            # Debug info
            if buy_signal.iloc[-1]:
                last = dataframe.iloc[-1]
                msg = [
                    f"🚀 BUY: {pair} ({self.market_regime})",
                    "\n".join(debug_info),
                    f"Price: {last['close_ha']:.6f}",
                    f"Support: {last['support']:.6f}",
                    f"Resistance: {last['resistance']:.6f}"
                ]
                logging.info("\n".join(msg))
                try:
                    if self.dp and hasattr(self.dp, 'send_msg'):
                        self.dp.send_msg("\n".join(msg))
                except Exception as e:
                    logging.error(f"Error sending message: {e}")

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']
        conditions = []
        
        # Dynamic profit thresholds
        if self.market_regime == "BULL":
            profit_threshold = self.sell_params["bull_profit_threshold"]
        else:
            profit_threshold = self.sell_params["choppy_profit_threshold"]
        
        # 1. Profit target
        profit_cond = dataframe['close_ha'] >= dataframe['open'] * (1 + profit_threshold)
        conditions.append(profit_cond)
        
        # 2. Resistance touch
        resistance_cond = dataframe['close_ha'] >= dataframe['resistance'] * 0.995
        conditions.append(resistance_cond)
        
        # 3. Max hold period
        if len(dataframe) > self.sell_params['max_hold_period']:
            max_hold = dataframe.index >= (dataframe.index[-1] - self.sell_params['max_hold_period'])
            conditions.append(max_hold)
        
        # Combine conditions
        sell_signal = reduce(lambda x, y: x | y, conditions)
        dataframe.loc[sell_signal, 'sell'] = 1
        
        # Debug info
        if sell_signal.iloc[-1]:
            last = dataframe.iloc[-1]
            reasons = []
            if profit_cond.iloc[-1]:
                profit_pct = (last['close_ha']/last['open']-1)*100
                reasons.append(f"Profit: {profit_pct:.2f}%")
            if resistance_cond.iloc[-1]:
                reasons.append(f"Resistance: {last['close_ha']:.6f} > {last['resistance']*0.995:.6f}")
            if 'max_hold' in locals() and max_hold.iloc[-1]:
                reasons.append("Max Hold")
                
            msg = [
                f"⛔ SELL: {pair} ({self.market_regime})",
                f"Reasons: {', '.join(reasons)}",
                f"Price: {last['close_ha']:.6f}"
            ]
            logging.info("\n".join(msg))
            try:
                if self.dp and hasattr(self.dp, 'send_msg'):
                    self.dp.send_msg("\n".join(msg))
            except Exception as e:
                logging.error(f"Error sending message: {e}")

        return dataframe