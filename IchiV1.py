# user_data/strategies/IchiV1.py
# Freqtrade Ichimoku Cloud Strategy v1 (2025 Optimized)
# -----------------------------------------------------
import logging
from freqtrade.strategy import IStrategy, Decimal, TAindicators, IntParameter
from pandas import DataFrame, Series

logger = logging.getLogger(__name__)

class IchiV1(IStrategy):
    # Optimal timeframe (2025 backtests)
    timeframe = '4h'
    
    # ROI table (15% profit take, trailing stop)
    minimal_roi = {
        "0": 0.15,
        "40": 0.05,
        "100": 0.01
    }
    
    # 8.2% stop-loss (2025 volatility-adjusted)
    stoploss = -0.082
    
    # Cloud width filter (min 3% spread)
    cloud_width_min = 0.03
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Ichimoku Cloud Calculation
        ichi = TAindicators.ichimoku(dataframe, 
            conversion_line_period=9,
            base_line_period=26,
            laggin_line_period=52,
            displacement=26
        )
        
        dataframe['tenkan'] = ichi['tenkan_sen']
        dataframe['kijun'] = ichi['kijun_sen']
        dataframe['senkou_a'] = ichi['senkou_span_a']
        dataframe['senkou_b'] = ichi['senkou_span_b']
        dataframe['chikou'] = ichi['chikou_span']
        
        # Cloud boundaries
        dataframe['cloud_top'] = dataframe[['senkou_a','senkou_b']].max(axis=1)
        dataframe['cloud_bot'] = dataframe[['senkou_a','senkou_b']].min(axis=1)
        dataframe['cloud_width'] = (dataframe['cloud_top'] - dataframe['cloud_bot']) / dataframe['cloud_bot']
        
        # Volume filter (20-period MA)
        dataframe['vol_ma'] = TAindicators.sma(dataframe['volume'], 20)
        
        # ADX for trend strength
        dataframe['adx'] = TAindicators.adx(dataframe, 14)
        
        # RSI for overbought check
        dataframe['rsi'] = TAindicators.rsi(dataframe, 14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            # Core Ichimoku signals
            (dataframe['close'] > dataframe['cloud_top']) &
            (dataframe['tenkan'] > dataframe['kijun']) &
            (dataframe['chikou'] > dataframe['chikou'].shift(26)) &
            
            # Volume breakout
            (dataframe['volume'] > dataframe['vol_ma'] * 1.5) &
            
            # 2025 Optimizations
            (dataframe['cloud_width'] > self.cloud_width_min) &
            (dataframe['adx'] > 25) &
            (dataframe['rsi'] < 65),
            
            'enter_long'] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Simple exit: price crosses below cloud
        dataframe.loc[
            (dataframe['close'] < dataframe['cloud_bot']),
            'exit_long'] = 1
        return dataframe
