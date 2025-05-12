from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class BitcoinMomentumStrategy(IStrategy):
    # Strategy settings
    timeframe = '1h'
    minimal_roi = {
        "0": 0.05
    }
    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Use only BTC
    startup_candle_count: int = 50
    process_only_new_candles = True
    use_custom_stoploss = False
    ignore_buying_expired_candle_after = 0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA indicators
        dataframe['ema9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema21'] = ta.EMA(dataframe, timeperiod=21)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema9'] > dataframe['ema21']) &
                (dataframe['rsi'] > 30) &
                (dataframe['macd'] > dataframe['macdsignal'])
            ),
            'buy'
        ] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['ema9'] < dataframe['ema21']) |
                (dataframe['rsi'] > 70)
            ),
            'sell'
        ] = 1
        return dataframe