from datetime import datetime
from collections import defaultdict

def get_user_inputs():
    """Returns predefined user inputs."""
    user_inputs = {
        "starting_capital": 15000,
        "monthly_contribution": 1000,
        "first_SL": 4,  # Percentage
        "first_PT": 15,  # Percentage
        "max_risk": 1.5,  # Percentage
        "user_defined_max": 5000,  # Maximum allowable trade cost
        "partial_sale_percentage": 30
    }
    return user_inputs


def trade_summary(trades):
    """
    Prints a summary of all trades, detailing entry, partial sale, adjustments, final sale, and total return.

    Args:
        trades (dict): Dictionary where keys are trade IDs and values are trade details.
    """
    print("\nTrade Summary:")
    print("-" * 50)

    for trade_id, trade in trades.items():
        # ----- ENTRY DETAILS -----
        # Convert entry date/time to "DD/MM/YYYY HH:MM" format.
        entry_date_str = (
            trade["entry_date"].strftime("%d/%m/%Y")
            if trade["entry_date"] else "N/A"
        )
        entry_price = trade["entry_price"]
        initial_amount = trade["initial_amount"]
        position_value = entry_price * initial_amount
        first_SL = trade["first_SL"]
        first_PT = trade["first_PT"]

        print(
            f"Entry {entry_date_str} @ ${entry_price:.2f} | "
            f"SL @ ${first_SL:.2f} | PT @ ${first_PT:.2f} | "
            f"Size: {initial_amount} shares | Position: ${position_value:.2f}"
        )

        # ----- ENTRY ADJUSTMENTS -----
        # We will print "Adjusted targets on ..." with **just the date**.
        for adjustment in trade["adjustments"]:
            if adjustment["adjustment_stage"] == "entry":
                # Convert the adjustment date/time but only print the date (DD/MM/YYYY)
                # for the "Adjusted targets on ..." line.
                if adjustment["adjustment_date"] is not None:
                    # Here is the key difference: we use "%d/%m/%Y" only
                    adjustment_date_str = adjustment["adjustment_date"].strftime("%d/%m/%Y")
                else:
                    adjustment_date_str = "N/A"

                adjusted_SL = adjustment["adjusted_SL"]
                adjusted_PT = adjustment["adjusted_PT"]

                print(
                    f"Adjusted targets on {adjustment_date_str} | "
                    f"SL @ ${adjusted_SL:.2f} | PT @ ${adjusted_PT:.2f}"
                )

        # ----- PARTIAL SALE -----
        if trade["partial_sale_done"]:
            # Convert partial sale date/time to "DD/MM/YYYY HH:MM"
            partial_sale_date_str = (
                trade["partial_sale_date"].strftime("%d/%m/%Y %H:%M")
                if trade["partial_sale_date"] else "N/A"
            )
            partial_sale_price = trade["partial_sale_price"]
            partial_sale_amount = trade["partial_sale_amount"]
            partial_sale_total = partial_sale_price * partial_sale_amount
            second_SL = trade["second_SL"]
            second_PT = trade["second_PT"]

            print(
                f"First profit target hit on {partial_sale_date_str} @ ${partial_sale_price:.2f} | "
                f"SL @ ${second_SL:.2f} | PT @ ${second_PT:.2f} | "
                f"Shares sold: {partial_sale_amount} | Total Sale: ${partial_sale_total:.2f}"
            )

            # ----- PARTIAL SALE ADJUSTMENTS -----
            # Again, let's do the same for partial adjustments: only date, no HH:MM.
            for adjustment in trade["adjustments"]:
                if adjustment["adjustment_stage"] == "partial":
                    if adjustment["adjustment_date"] is not None:
                        adjustment_date_str = adjustment["adjustment_date"].strftime("%d/%m/%Y")
                    else:
                        adjustment_date_str = "N/A"
                    adjusted_SL = adjustment["adjusted_SL"]
                    adjusted_PT = adjustment["adjusted_PT"]
                    print(
                        f"Adjusted targets on {adjustment_date_str} | "
                        f"SL @ ${adjusted_SL:.2f} | PT @ ${adjusted_PT:.2f}"
                    )

        # ----- FINAL (OR REMAINING) SALE -----
        # Convert final sale date/time to "DD/MM/YYYY HH:MM"
        remaining_date_str = (
            trade["remaining_date"].strftime("%d/%m/%Y %H:%M")
            if trade["remaining_date"] else "N/A"
        )
        remaining_price = trade["remaining_price"]
        remaining_sale_amount = trade["remaining_sale_amount"]
        final_sale_total = remaining_price * remaining_sale_amount

        # Map 'adjusted_SL' -> 'Stop loss' or 'adjusted_PT' -> 'Profit target'
        # If your logic sets "remaining_reason" to "End of Simulation", you might want a fallback label.
        if trade["remaining_reason"] == "adjusted_SL":
            reason_str = "Stop loss"
        elif trade["remaining_reason"] == "adjusted_PT":
            reason_str = "Profit target"
        else:
            reason_str = "End of Simulation"

        print(
            f"{reason_str} hit on {remaining_date_str} @ ${remaining_price:.2f} | "
            f"Shares sold: {remaining_sale_amount} | Total Sale: ${final_sale_total:.2f}."
        )

        # ----- TOTAL RETURN -----
        total_sale_value = (
            (partial_sale_total if trade["partial_sale_done"] else 0) + final_sale_total
        )
        total_return_percentage = ((total_sale_value / position_value) - 1) * 100 if position_value != 0 else 0
        total_return_dollars = total_sale_value - position_value

        print(f"Total Return: {total_return_percentage:.2f}% (${total_return_dollars:.2f}).")
        print("-" * 50)

    print("End of Trade Summary")




def final_summary(trades, budget_manager, stock_data, ticker):
    """
    Prints a final summary of the trading simulation.

    Args:
        trades (dict): Dictionary of trades grouped by ticker.
        budget_manager (BudgetManager): Manages liquidity and contributions.
        stock_data (pd.DataFrame): Stock data used in the simulation.
        ticker (str): Ticker symbol of the stock being traded.
    """
    # Initialize metrics
    total_trades = 0
    total_winning_trades = 0
    total_losing_trades = 0
    total_profit = 0
    total_capital = budget_manager.get_total_liquidity()
    total_contributions = budget_manager.get_total_contributions()
    total_hold_time_days = 0  # Sum of all hold times

    # Lists to store individual trade returns for computing average win/loss
    winning_returns = []
    losing_returns = []

    # Process each trade
    for trade_id, trade in trades.items():
        total_trades += 1

        # Calculate total sale value
        partial_sale_value = (trade["partial_sale_amount"] * trade["partial_sale_price"]
                              if trade["partial_sale_done"] else 0)
        remaining_sale_value = trade["remaining_sale_amount"] * trade["remaining_price"]
        total_trade_profit = (partial_sale_value + remaining_sale_value) - (
            trade["entry_price"] * trade["initial_amount"])

        # Trade return percentage
        entry_cost = trade["entry_price"] * trade["initial_amount"]
        trade_return_percentage = (total_trade_profit / entry_cost * 100) if entry_cost != 0 else 0

        # Update total profit
        total_profit += total_trade_profit

        # Determine winning/losing trade
        if (trade["partial_sale_done"] and trade["partial_sale_price"] > trade["entry_price"]) or \
           (trade["remaining_price"] > trade["entry_price"]):
            total_winning_trades += 1
            winning_returns.append(trade_return_percentage)
        else:
            total_losing_trades += 1
            losing_returns.append(trade_return_percentage)

        # Calculate hold time for the trade
        entry_date = trade["entry_date"]
        remaining_date = trade["remaining_date"]
        hold_time_days = (remaining_date - entry_date).days
        total_hold_time_days += hold_time_days

    # Calculate final metrics
    win_rate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_return_percentage = ((total_capital / total_contributions) - 1) * 100 if total_contributions != 0 else 0
    average_hold_time_days = (total_hold_time_days / total_trades) if total_trades > 0 else 0

    # Compute average win/loss
    average_win = sum(winning_returns) / len(winning_returns) if winning_returns else 0
    average_loss = sum(losing_returns) / len(losing_returns) if losing_returns else 0

    # Stock performance
    initial_price = stock_data.iloc[0]["Close"]
    final_price = stock_data.iloc[-1]["Close"]
    stock_return = ((final_price / initial_price - 1) * 100)

    # S&P return for the period
    sp_data = stock_data["Index"].iloc[0] if "Index" in stock_data.columns else "N/A"
    sp_return = sp_data * 100 if isinstance(sp_data, (float, int)) else "N/A"

    # Compute commissions after all trades processed
    total_commissions = calculate_commissions(trades)

    # Compute return after commissions
    if total_contributions != 0:
        return_after_commissions = (((total_capital - total_commissions) / total_contributions) - 1) * 100
    else:
        return_after_commissions = 0

    # Print summary
    print("\nFinal Summary:")
    print("-" * 50)
    print(
        f"Total Profit/Loss: ${total_profit:.2f}  | Total Return: {total_return_percentage:.2f}%  | "
        f"Total Capital: ${total_capital:.2f} | Total Contributions: ${total_contributions:.2f}"
    )
    print(
        f"Total Trades Executed: {total_trades} | Winning Trades: {total_winning_trades} | "
        f"Losing Trades: {total_losing_trades} | Win Rate: {win_rate:.2f}%"
    )
    print(
        f"Average Position Hold Time: {average_hold_time_days:.1f} days | "
        f"Average win: {average_win:.2f}% | Average loss: {average_loss:.2f}%"
    )
    print(
        f"Commissions: ${total_commissions:.2f} | Return After Commissions: {return_after_commissions:.2f}%"
    )
    print(
        f"Ticker Traded: {ticker}\n"
        f"{ticker} Performance: ${initial_price:.2f} -> ${final_price:.2f} ({stock_return:.2f}%). "
        f"S&P Return: {sp_return if isinstance(sp_return, str) else f'{sp_return:.2f}%'}."
    )
    print("-" * 50)

def calculate_commissions(trades):
    """
    Calculates the total commissions paid for all trades based on Interactive Brokers fee structure.

    For each trade, commissions are charged on:
        - The entry (buy order)
        - The partial sale (if any)
        - The remaining sale (closing the position)

    Commission rules:
    - US Trades: $0.005 per share.
    - Minimum per order: $1.
    - Maximum per order: 1% of the trade value (shares * execution_price).

    Args:
        trades (dict): Dictionary of all trades.

    Returns:
        float: The total commissions paid.
    """
    total_commissions = 0.0

    def commission_for_order(shares, price):
        if shares <= 0:
            return 0.0
        # Calculate raw commission
        raw_commission = shares * 0.005
        trade_value = shares * price
        # Apply minimum and maximum
        commission = max(raw_commission, 1.0)  # minimum $1
        commission = min(commission, 0.01 * trade_value)  # max 1% of trade value
        return commission

    for trade_id, trade in trades.items():
        # Entry commission
        entry_shares = trade["initial_amount"]
        entry_price = trade["entry_price"]
        total_commissions += commission_for_order(entry_shares, entry_price)

        # Partial sale commission (if applicable)
        if trade["partial_sale_done"] and trade["partial_sale_amount"] and trade["partial_sale_price"]:
            partial_shares = trade["partial_sale_amount"]
            partial_price = trade["partial_sale_price"]
            total_commissions += commission_for_order(partial_shares, partial_price)

        # Remaining sale commission
        # At end of trade, remaining shares are sold at remaining_price
        if trade["remaining_sale_amount"] and trade["remaining_price"]:
            remaining_shares = trade["remaining_sale_amount"]
            remaining_price = trade["remaining_price"]
            total_commissions += commission_for_order(remaining_shares, remaining_price)

    return total_commissions


