import pandas as pd
from indicator_conditions import (
    rsi_condition,
    macd_condition,
    ema_10_condition,
    ema_20_condition,
    ema_50_condition,
    ema_100_condition,
    ema_200_condition,
    sma_5_10_condition,
    ema_50_avg_condition,
    high_avg_condition,
    prev_close_greater_than_open_condition,
    ema_100_prev_close_condition
)

class BudgetManager:
    def __init__(self, starting_capital, monthly_contribution):
        self.starting_capital = starting_capital
        self.monthly_contribution = monthly_contribution
        self.total_liquidity = starting_capital
        self.total_contributions = starting_capital  # Start with initial capital
        self.current_month = None

    def add_monthly_contribution(self, current_date):
        month = current_date.month
        year = current_date.year
        if self.current_month != (year, month):
            self.total_liquidity += self.monthly_contribution
            self.total_contributions += self.monthly_contribution
            self.current_month = (year, month)

    def remove_capital(self, amount):
        if amount > self.total_liquidity:
            raise ValueError("Insufficient liquidity to complete the transaction.")
        self.total_liquidity -= amount

    def add_capital(self, amount):
        self.total_liquidity += amount

    def get_total_liquidity(self):
        return self.total_liquidity

    def get_total_contributions(self):
        return self.total_contributions

def entry_conditions(data_df, indicators_df, current_index, budget_manager, max_risk, stop_loss, open_positions):
    conditions_library = {
        'rsi_condition': False,
        'macd_condition': False,
        'ema_10_condition': False,
        'ema_20_condition': False,
        'ema_50_condition': False,
        'ema_100_condition': False,
        'ema_200_condition': False,
        'sma_5_10_condition': True,
        'ema_50_avg_condition': True,
        'high_avg_condition': True, #toimib
        'prev_close_greater_than_open': True, #toimib
        'ema_100_prev_close': True #toimib
    }

    try:
        # Set entry price to the current day's Open price
        entry_price = data_df.loc[current_index, 'Open']

        # Check liquidity and risk conditions
        liquidity = budget_manager.get_total_liquidity()
        liquidity_condition = liquidity >= entry_price
        risk_condition = (liquidity * max_risk / stop_loss) >= 1000

        if not (liquidity_condition and risk_condition):
            return False

        # Calculate the proposed first profit target for the new trade
        #proposed_first_PT = entry_price * (1 + stop_loss / 100)

        # New condition: Check if proposed PT is more than 2% below any adjusted PT of open positions
        #for key, position in open_positions.items():
            if proposed_first_PT < position["adjusted_PT"] * 0.99:
                return False

        # Map conditions to their respective functions
        condition_functions = {
            'rsi_condition': lambda: rsi_condition(indicators_df.loc[current_index, 'RSI']),
            'macd_condition': lambda: macd_condition(indicators_df, current_index),
            'ema_10_condition': lambda: ema_10_condition(entry_price, indicators_df, current_index),
            'ema_20_condition': lambda: ema_20_condition(entry_price, indicators_df, current_index),
            'ema_50_condition': lambda: ema_50_condition(entry_price, indicators_df, current_index),
            'ema_100_condition': lambda: ema_100_condition(entry_price, indicators_df, current_index),
            'ema_200_condition': lambda: ema_200_condition(entry_price, indicators_df, current_index),
            'sma_5_10_condition': lambda: sma_5_10_condition(indicators_df, current_index),
            'ema_50_avg_condition': lambda: ema_50_avg_condition(indicators_df, current_index),
            'high_avg_condition': lambda: high_avg_condition(data_df, current_index),
            'prev_close_greater_than_open': lambda: prev_close_greater_than_open_condition(data_df, current_index),
            'ema_100_prev_close': lambda: ema_100_prev_close_condition(indicators_df, data_df, current_index)
        }

        # Evaluate enabled conditions
        for condition, enabled in conditions_library.items():
            if enabled and not condition_functions[condition]():
                return False

        # Return the entry price if all conditions are met
        return entry_price

    except KeyError as e:
        raise KeyError(f"KeyError in entry_conditions: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error in entry_conditions: {e}")

def calculate_trade_size(budget_manager, entry_price, max_risk, stop_loss, user_defined_max):
    """
    Calculates the trade size based on portfolio value, risk, stop-loss, and user-defined maximum.
    Ensures that the total trade cost does not exceed user-defined maximum.
    
    Returns:
    tuple: (int: trade size, float: cost of trade)
    """
    try:
        # Get available liquidity
        available_liquidity = budget_manager.get_total_liquidity()

        # Validate inputs
        if max_risk <= 0 or stop_loss <= 0 or entry_price <= 0:
            raise ValueError("max_risk, stop_loss, and entry_price must be greater than zero.")

        # Calculate the maximum risk amount
        risk_amount = available_liquidity * (max_risk / 100)

        # Calculate the maximum trade size based on risk and stop-loss percentage
        max_trade_size_by_risk = risk_amount / (entry_price * (stop_loss / 100))

        # Determine the cost of trade based on the calculated trade size
        calculated_trade_size = int(max_trade_size_by_risk)
        cost_of_trade = calculated_trade_size * entry_price

        # Adjust trade size if the cost exceeds the user-defined max
        if cost_of_trade > user_defined_max:
            adjusted_trade_size = int(user_defined_max / entry_price)
            cost_of_trade = adjusted_trade_size * entry_price
        else:
            adjusted_trade_size = calculated_trade_size

        # Return the final trade size and cost
        return adjusted_trade_size, cost_of_trade

    except ValueError as e:
        raise ValueError(f"Input error in calculate_trade_size: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error in calculate_trade_size: {e}")

