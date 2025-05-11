from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import requests
import datetime

class HybridNewsStrategy(IStrategy):
    minimal_roi = {
        "0": 0.15
    }

    stoploss = -0.1
    timeframe = '5m'

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.api_key = '5a52b1f08bc0dea71399e6d35298efc0cc712553'
        self.news_sentiment = 0  # -1 = bad, 0 = neutral, 1 = good

    def fetch_sentiment(self):
        try:
            today = datetime.date.today().isoformat()
            url = f'https://cryptopanic.com/api/v1/posts/?auth_token={self.api_key}&filter=hot&public=true'
            response = requests.get(url)
            if response.status_code == 200:
                articles = response.json().get('results', [])
                positive = sum(1 for a in articles if a.get('positive'))
                negative = sum(1 for a in articles if a.get('negative'))
                if positive > negative:
                    self.news_sentiment = 1
                elif negative > positive:
                    self.news_sentiment = -1
                else:
                    self.news_sentiment = 0
        except Exception as e:
            self.news_sentiment = 0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        self.fetch_sentiment()
        dataframe['rsi'] = dataframe['close'].rolling(window=14).apply(
            lambda x: (x.diff().apply(lambda y: y if y > 0 else 0).mean() /
                       abs(x.diff()).mean()) * 100 if len(x) > 1 else 0
        )
        dataframe['ema'] = dataframe['close'].ewm(span=50, adjust=False).mean()
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] > dataframe['ema']) &
                (self.news_sentiment == 1)
            ),
            'buy'
        ] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) |
                (self.news_sentiment == -1)
            ),
            'sell'
        ] = 1
        return dataframe
