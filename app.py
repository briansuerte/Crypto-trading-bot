from flask import Flask, jsonify
import requests

app = Flask(__name__)

def fetch_prices(symbol='bitcoin', currency='usd', days=30):
    url = f'https://api.coingecko.com/api/v3/coins/{symbol}/market_chart'
    params = {'vs_currency': currency, 'days': days}
    response = requests.get(url, params=params)
    data = response.json()
    prices = [price[1] for price in data['prices']]
    return prices

def compute_rsi(prices, period=14):
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_moving_average(prices, period):
    return sum(prices[-period:]) / period

def analyze_market():
    prices = fetch_prices()
    if len(prices) < 50:
        return {'status': 'Not enough data'}
    short_ma = compute_moving_average(prices, 10)
    long_ma = compute_moving_average(prices, 30)
    rsi = compute_rsi(prices, 14)

    if rsi > 70 and short_ma < long_ma:
        action = 'SELL'
    elif rsi < 30 and short_ma > long_ma:
        action = 'BUY'
    else:
        action = 'HOLD'

    return {
        'short_ma': short_ma,
        'long_ma': long_ma,
        'rsi': rsi,
        'action': action
    }

@app.route('/')
def home():
    return jsonify(analyze_market())

if __name__ == '__main__':
    app.run(debug=True)
