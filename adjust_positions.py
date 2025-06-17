def set_adjusted_for_new_position(open_positions, key):
    """
    Adjust SL/PT to first_SL/PT if unset or less favorable.
    """
    position = open_positions[key]

    if not position["partial_sale_done"]:
        if position["adjusted_SL"] is None or position["adjusted_SL"] < position["first_SL"]:
            position["adjusted_SL"] = position["first_SL"]
        if position["adjusted_PT"] is None or position["adjusted_PT"] < position["first_PT"]:
            position["adjusted_PT"] = position["first_PT"]


def set_adjusted_for_partial_sale(open_positions, key):
    """
    Adjust SL/PT to second_SL/PT if unset or less favorable.
    """
    position = open_positions[key]

    if position["partial_sale_done"]:
        if position["adjusted_SL"] is None or position["adjusted_SL"] < position["second_SL"]:
            position["adjusted_SL"] = position["second_SL"]
        if position["adjusted_PT"] is None or position["adjusted_PT"] < position["second_PT"]:
            position["adjusted_PT"] = position["second_PT"]

def update_all_positions(open_positions, current_date):
    """
    Update all positions to include the most favorable SL/PT for open positions and log adjustments.
    Returns:
        None: Updates open_positions directly.
    """
    # Group positions by ticker
    ticker_groups = {}
    for key, position in open_positions.items():
        ticker = position["ticker"]
        ticker_groups.setdefault(ticker, []).append(key)

    # Find and apply the most favorable SL/PT for each group
    for ticker, keys in ticker_groups.items():
        highest_SL = float('-inf')
        highest_PT = float('-inf')

        # Determine the highest SL and PT in the group
        for key in keys:
            position = open_positions[key]
            if position["adjusted_SL"] is not None:
                highest_SL = max(highest_SL, position["adjusted_SL"])
            if position["adjusted_PT"] is not None:
                highest_PT = max(highest_PT, position["adjusted_PT"])

        # Apply the highest SL and PT to all positions and log adjustments
        for key in keys:
            position = open_positions[key]
            adjustment_stage = "entry" if not position["partial_sale_done"] else "partial"

            # Update SL and PT
            position["adjusted_SL"] = highest_SL
            position["adjusted_PT"] = highest_PT

            # Log the adjustment
            position["adjustments"].append({
                "adjustment_date": current_date,
                "adjusted_SL": highest_SL,
                "adjusted_PT": highest_PT,
                "adjustment_stage": adjustment_stage
            })
