# Define parameters
stop_loss_percentage = 0.02   # 2% Stop Loss
take_profit_percentage = 0.04  # 4% Take Profit
trailing_stop_percentage = 0.03  # 3% Trailing Stop
risk_per_trade = 0.01   # 1% of Account Balance risk per trade
ema_period = 50         # 50-period Exponential Moving Average (EMA)
macd_short_period = 12  # MACD Short Period
macd_long_period = 26   # MACD Long Period
macd_signal_period = 9  # MACD Signal Period
rsi_period = 14         # Relative Strength Index (RSI) Period

# Functions for indicators
def calculate_ema(prices, period):
    # EMA calculation (exponentially weighted moving average)
    return prices.ewm(span=period).mean()

def calculate_macd(prices, short_period, long_period, signal_period):
    # Calculate MACD line and Signal line
    macd_line = prices.ewm(span=short_period).mean() - prices.ewm(span=long_period).mean()
    macd_signal_line = macd_line.ewm(span=signal_period).mean()
    return macd_line, macd_signal_line

def calculate_rsi(prices, period):
    # Calculate Relative Strength Index (RSI)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Define entry conditions
def should_enter_trade(prices, balance, current_position):
    # Calculate indicators
    ema = calculate_ema(prices, ema_period)
    macd_line, macd_signal_line = calculate_macd(prices, macd_short_period, macd_long_period, macd_signal_period)
    rsi = calculate_rsi(prices, rsi_period)
    
    # Entry conditions for long position (buy)
    if prices[-1] > ema[-1] and macd_line[-1] > macd_signal_line[-1] and rsi[-1] < 70:
        if current_position == 0:  # No open position
            position_size = balance * risk_per_trade  # Risking 1% of balance per trade
            return "long", position_size

    # Entry conditions for short position (sell)
    elif prices[-1] < ema[-1] and macd_line[-1] < macd_signal_line[-1] and rsi[-1] > 30:
        if current_position == 0:  # No open position
            position_size = balance * risk_per_trade  # Risking 1% of balance per trade
            return "short", position_size

    return None, 0

# Define stop loss and take profit
def set_stop_loss_take_profit(entry_price, direction):
    if direction == "long":
        stop_loss = entry_price * (1 - stop_loss_percentage)
        take_profit = entry_price * (1 + take_profit_percentage)
    elif direction == "short":
        stop_loss = entry_price * (1 + stop_loss_percentage)
        take_profit = entry_price * (1 - take_profit_percentage)
    
    return stop_loss, take_profit

# Define trailing stop logic
def update_trailing_stop(current_price, entry_price, direction, trailing_stop):
    if direction == "long":
        if current_price > entry_price * (1 + trailing_stop_percentage):
            trailing_stop = max(trailing_stop, current_price * (1 - trailing_stop_percentage))
    elif direction == "short":
        if current_price < entry_price * (1 - trailing_stop_percentage):
            trailing_stop = min(trailing_stop, current_price * (1 + trailing_stop_percentage))
    
    return trailing_stop

# Define exit conditions
def should_exit_trade(current_price, entry_price, stop_loss, take_profit, trailing_stop, direction):
    if direction == "long":
        if current_price <= stop_loss or current_price >= take_profit or current_price <= trailing_stop:
            return "exit"
    elif direction == "short":
        if current_price >= stop_loss or current_price <= take_profit or current_price >= trailing_stop:
            return "exit"
    
    return "hold"

# Example trading loop
balance = 10000  # Starting balance
current_position = 0  # No open position (1 = long, -1 = short)
entry_price = 0
stop_loss = 0
take_profit = 0
trailing_stop = 0

# Assuming 'prices' is a time series of closing prices
for i in range(1, len(prices)):
    # Check if we should enter a trade
    direction, position_size = should_enter_trade(prices[:i], balance, current_position)
    if direction and position_size > 0:
        current_position = direction
        entry_price = prices[i]
        stop_loss, take_profit = set_stop_loss_take_profit(entry_price, direction)
        trailing_stop = entry_price  # Set initial trailing stop at entry price
    
    # Check if we should exit a trade
    if current_position != 0:
        action = should_exit_trade(prices[i], entry_price, stop_loss, take_profit, trailing_stop, current_position)
        if action == "exit":
            current_position = 0  # Close the position
            print(f"Exited at {prices[i]} with {action} action")
        
        # Update trailing stop
        trailing_stop = update_trailing_stop(prices[i], entry_price, current_position, trailing_stop)
