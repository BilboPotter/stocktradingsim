def sma_5_10_condition(indicators_df, current_index):
    """
    Checks if SMA5 > SMA10 for the previous day.
    Returns:
        bool: True if SMA5 > SMA10 for the previous day, False otherwise.
    """
    if current_index:  # Ensure there's a previous day to compare
        sma_5_prev = indicators_df.loc[current_index - 1, 'SMA_5']
        sma_10_prev = indicators_df.loc[current_index - 1, 'SMA_10']
        return sma_5_prev > sma_10_prev
    return False

def high_avg_condition(data_df, current_index):
    """
    Checks if the previous day's High > average High of the previous 10 days.

    Parameters:
        data_df (pd.DataFrame): DataFrame containing market data (e.g., High prices).
        current_index (int): Index of the current day in the DataFrame.

    Returns:
        bool: True if the previous day's High > average High of the last 10 days, False otherwise.
    """
    if current_index:  # Ensure there are at least 10 previous days to calculate the average
        high_prev = data_df.loc[current_index - 1, 'High']
        high_last_10 = data_df.loc[current_index - 10:current_index - 1, 'High'].mean()
        return high_prev > high_last_10
    return False

def ema_50_avg_condition(indicators_df, current_index):
    """
    Checks if the previous day's EMA50 > average EMA50 of the previous 10 days.

    Returns:
        bool: True if the previous day's EMA50 > average EMA50 of the last 10 days, False otherwise.
    """
    if current_index:  # Ensure there are at least 10 previous days to calculate the average
        ema_50_prev = indicators_df.loc[current_index - 1, 'EMA_50']
        ema_50_last_10 = indicators_df.loc[current_index - 11:current_index - 1, 'EMA_50'].mean()
        return ema_50_prev > ema_50_last_10
    return False

def prev_close_greater_than_open_condition(data_df, current_index):
    """
    Checks if the previous day's Close is >= 98.5% of the previous day's Open.

    Returns:
        bool: True if Close >= 98.5% of Open, False otherwise.
    """
    if current_index:
        prev_close = data_df.loc[current_index - 1, 'Close']
        prev_open = data_df.loc[current_index - 1, 'Open']
        return prev_close >= 0.985 * prev_open
    return False


def ema_100_prev_close_condition(indicators_df, data_df, current_index):
    """
    Checks if EMA100 is >= 99% of the previous day's Close.

    Returns:
        bool: True if EMA100 >= 99% of previous Close, False otherwise.
    """
    if current_index:
        ema_100 = indicators_df.loc[current_index - 1, 'EMA_100']
        prev_close = data_df.loc[current_index - 1, 'Close']
        return ema_100 <= 0.99 * prev_close
    return False

def rsi_condition(rsi_value, threshold_oversold=30, threshold_overbought=55):
    """
    RSI is oversold (< threshold_oversold) or overbought (> threshold_overbought).
    """
    if rsi_value > 40 and rsi_value < 70:
        rsi = True
    else:
        rsi = False
        
    return rsi
    #return rsi_value < threshold_oversold or rsi_value > threshold_overbought


def macd_condition(indicators_df, current_index):
    """
    MACD histogram is increasing.
    """
    if current_index >= 2:
        macd_hist_day_2 = indicators_df.loc[current_index - 2, 'MACD_Histogram']
        macd_hist_day_1 = indicators_df.loc[current_index - 1, 'MACD_Histogram']
        return macd_hist_day_2 < macd_hist_day_1
    return False


def ema_10_condition(entry_price, indicators_df, current_index):
    """
    Entry price > EMA 10.
    """
    ema_10 = indicators_df.loc[current_index, 'EMA_10']
    return entry_price > ema_10


def ema_20_condition(entry_price, indicators_df, current_index):
    """
    Entry price > EMA 20.
    """
    ema_20 = indicators_df.loc[current_index, 'EMA_20']
    return entry_price > ema_20


def ema_50_condition(entry_price, indicators_df, current_index):
    """
    Entry price > EMA 50.
    """
    ema_50 = indicators_df.loc[current_index, 'EMA_50']
    return entry_price > ema_50


def ema_100_condition(entry_price, indicators_df, current_index):
    """
    Entry price > EMA 100.
    """
    ema_100 = indicators_df.loc[current_index, 'EMA_100']
    return entry_price > ema_100


def ema_200_condition(entry_price, indicators_df, current_index):
    """
    Entry price > EMA 200.
    """
    ema_200 = indicators_df.loc[current_index, 'EMA_200']
    return entry_price > ema_200
