from price_entry_tradesize import BudgetManager, entry_conditions, calculate_trade_size
from data_loader import load_data
from Indicators import calculate_indicators
from user_io import get_user_inputs, final_summary, trade_summary
from adjust_positions import (
    set_adjusted_for_new_position,
    set_adjusted_for_partial_sale,
    update_all_positions
)
import pandas as pd
import trades_to_sheets

# Constants for data loading
SHEET_URL = "google sheets url"
CREDENTIALS_PATH = r"fourth-gantry file"

# Manually specify which sheets to load
DAILY_SHEET_NAME = "Sheet1"      # daily sheet containing 'Stock' column
INTRADAY_SHEET_NAME = "VRT30"   # or "TSLA30", "MSFT30", etc.

def get_new_key(trade_dict):
    """
    Generate the next numeric key for the dictionary.
    """
    return max(trade_dict.keys(), default=0) + 1

def trading_loop():
    """
    Simulates a basic trading loop by iterating over daily_data
    for entry signals, and intraday data for SL/PT exits.
    """

    # Step 1: Load user inputs
    user_inputs = get_user_inputs()

    # Step 2: Initialize BudgetManager
    budget_manager = BudgetManager(
        starting_capital=user_inputs["starting_capital"],
        monthly_contribution=user_inputs["monthly_contribution"]
    )

    # Step 3: Load daily & intraday data
    # Returns: (daily_data, intraday_data, ticker_from_daily)
    stock_data, intraday_data, ticker_from_daily = load_data(
        sheet_url=SHEET_URL,
        credentials_path=CREDENTIALS_PATH,
        daily_sheet=DAILY_SHEET_NAME,
        intraday_sheet=INTRADAY_SHEET_NAME
    )

    # If we found a ticker in the daily data, keep it; else default to something
    ticker = ticker_from_daily if ticker_from_daily else "Unknown"

    # Step 3a: Compute indicators on the full daily dataset
    full_data_with_indicators = calculate_indicators(stock_data)

    # Step 3b: Filter daily data from a chosen start date
    filtered_data = full_data_with_indicators[full_data_with_indicators['Date'] >= '2024-01-01'].copy()
    filtered_data.reset_index(drop=True, inplace=True)

    # Step 3c: Filter intraday data similarly + group by date
    intraday_by_date = {}
    if intraday_data is not None:
        intraday_data = intraday_data[intraday_data['Datetime'] >= '2024-01-01'].copy()
        intraday_data.reset_index(drop=True, inplace=True)

        intraday_by_date = {
            date_val: df_group
            for date_val, df_group in intraday_data.groupby(intraday_data['Datetime'].dt.date)
        }

    # We'll just reassign these for clarity
    stock_data = filtered_data
    indicators = filtered_data

    # Step 4: Initialize tracking variables
    trades = {}
    open_positions = {}
    last_trade_date = None

    # Step 5: Iterate over daily data
    for current_index in range(len(stock_data)):
        current_date = stock_data.loc[current_index, 'Date']
        budget_manager.add_monthly_contribution(current_date)

        # Prevent multiple trades on same date (if desired)
        if last_trade_date == current_date:
            continue

        # (a) Check entry (daily)
        entry_price = entry_conditions(
            stock_data,
            indicators,
            current_index,
            budget_manager,
            user_inputs["max_risk"],
            user_inputs["first_SL"],
            open_positions
        )

        if entry_price:
            # (b) Calculate trade size
            initial_amount, total_cost = calculate_trade_size(
                budget_manager,
                entry_price,
                user_inputs["max_risk"],
                user_inputs["first_SL"],
                user_inputs["user_defined_max"]
            )

            # (c) Enter trade
            budget_manager.remove_capital(total_cost)
            new_key = get_new_key(trades)
            new_trade = {
                "ticker": ticker,
                "entry_price": entry_price,
                "entry_date": current_date,  # daily date (for reference)
                "initial_amount": initial_amount,
                "first_SL": entry_price * (1 - user_inputs["first_SL"] / 100),
                "first_PT": entry_price * (1 + user_inputs["first_PT"] / 100),
                "partial_sale_done": False,
                "partial_sale_date": None,
                "partial_sale_price": None,
                "partial_sale_amount": None,
                "remaining_sale_amount": None,
                "second_SL": None,
                "second_PT": None,
                "adjusted_SL": None,
                "adjusted_PT": None,
                "adjustments": [],
                "remaining_reason": None,
                "remaining_date": None,
                "remaining_price": None
            }
            trades[new_key] = new_trade
            open_positions[new_key] = new_trade

            # Apply entry adjustments
            set_adjusted_for_new_position(open_positions, new_key)
            update_all_positions(open_positions, current_date)

        # (d) Intraday SL/PT checks
        closed_trades = []
        day_key = current_date.date()
        intraday_bars_for_today = intraday_by_date.get(day_key, pd.DataFrame())

        if not intraday_bars_for_today.empty:
            intraday_bars_for_today.sort_values(by='Datetime', inplace=True)
            for row_index, bar in intraday_bars_for_today.iterrows():
                open_price = bar['Open']
                low_price = bar['Low']
                high_price = bar['High']
                this_bar_time = bar['Datetime']  # This is the full intraday timestamp

                trades_to_remove = []
                for key, position in open_positions.items():
                    sl_price = position["adjusted_SL"]
                    pt_price = position["adjusted_PT"]

                    # If partial sale not done yet
                    if not position["partial_sale_done"]:
                        # Stop-loss
                        if open_price <= sl_price:
                            execution_price = open_price
                        elif low_price < sl_price:
                            execution_price = sl_price
                        else:
                            execution_price = None

                        if execution_price is not None:
                            position["remaining_reason"] = "adjusted_SL"
                            # Store the actual intraday timestamp (bar["Datetime"])
                            position["remaining_date"] = this_bar_time
                            position["remaining_price"] = execution_price
                            position["remaining_sale_amount"] = position["initial_amount"]
                            budget_manager.add_capital(execution_price * position["initial_amount"])
                            trades_to_remove.append(key)
                            continue

                        # Profit-target
                        if open_price >= pt_price:
                            execution_price = open_price
                        elif high_price > pt_price:
                            execution_price = pt_price
                        else:
                            execution_price = None

                        if execution_price is not None:
                            partial_sale_amount = position["initial_amount"] * user_inputs["partial_sale_percentage"] // 100
                            position["partial_sale_done"] = True
                            # Store the actual intraday timestamp
                            position["partial_sale_date"] = this_bar_time
                            position["partial_sale_price"] = execution_price
                            position["partial_sale_amount"] = partial_sale_amount
                            position["remaining_sale_amount"] = position["initial_amount"] - partial_sale_amount
                            budget_manager.add_capital(partial_sale_amount * execution_price)

                            # Now define second SL/PT
                            position["second_SL"] = position["adjusted_PT"] * (1 - user_inputs["first_SL"] / 100)
                            position["second_PT"] = position["adjusted_PT"] * (1 + user_inputs["first_PT"] / 100)
                            set_adjusted_for_partial_sale(open_positions, key)

                    # If partial sale done
                    if position["partial_sale_done"]:
                        # Re-fetch the updated SL/PT
                        sl_price = position["adjusted_SL"]
                        pt_price = position["adjusted_PT"]

                        if open_price <= sl_price:
                            execution_price = open_price
                        elif low_price < sl_price:
                            execution_price = sl_price
                        elif open_price >= pt_price:
                            execution_price = open_price
                        elif high_price > pt_price:
                            execution_price = pt_price
                        else:
                            execution_price = None

                        if execution_price is not None:
                            reason = "adjusted_SL" if execution_price <= sl_price else "adjusted_PT"
                            position["remaining_reason"] = reason
                            # Store the actual intraday timestamp
                            position["remaining_date"] = this_bar_time
                            position["remaining_price"] = execution_price
                            budget_manager.add_capital(execution_price * position["remaining_sale_amount"])
                            trades_to_remove.append(key)

                # Remove any fully closed positions this bar
                for k in trades_to_remove:
                    closed_trades.append(k)
                    open_positions.pop(k, None)

        last_trade_date = current_date

    # Step 6: End of simulation – close open positions at final daily close
    if not stock_data.empty:
        final_close_price = stock_data.iloc[-1]['Close']
        final_date = stock_data.iloc[-1]['Date']
        for key, position in open_positions.items():
            current_price = final_close_price
            position["remaining_reason"] = "End of Simulation"
            # We keep this final_date as the daily date, unless you prefer to store intraday time. 
            # Typically there's no intraday bar for the end of data, so we just store final_date.
            position["remaining_date"] = final_date
            position["remaining_price"] = current_price
            # If no partial sale was done, all shares remain. Otherwise we have leftover.
            position["remaining_sale_amount"] = (
                position["initial_amount"] if not position["partial_sale_done"]
                else position["remaining_sale_amount"]
            )
            budget_manager.add_capital(current_price * position["remaining_sale_amount"])

    # Step 7: Summaries
    trade_summary(trades)
    final_summary(trades, budget_manager, stock_data, ticker)


    # Step 8: Save trades to Google Sheets if needed
    trades_to_sheets.save_trade_data(trades, full_data_with_indicators)


if __name__ == "__main__":
    trading_loop()
