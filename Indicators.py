import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

def calculate_indicators_for_dates(data, dates):
    """
    Calculate indicators for specific dates.
    If indicators are not already calculated (e.g., EMA_10 not in columns), 
    they will be computed once. Otherwise, existing indicators are used.

    Args:
        data (pd.DataFrame): Trading data containing necessary columns (Date, Close, etc.).
        dates (list): List of dates (in 'YYYY-MM-DD' format) for which indicators are needed.

    Returns:
        dict: Dictionary mapping each date (string in 'YYYY-MM-DD') to its calculated indicators.
    """
    # Check if indicators are already present. If not, calculate them.
    if 'EMA_10' not in data.columns:
        data = calculate_indicators(data)
    else:
        # Ensure data is sorted by Date if not already
        if not data['Date'].is_monotonic_increasing:
            data = data.sort_values('Date').reset_index(drop=True)

    indicators = {}
    # Convert each date string to a datetime object and then extract the row
    for d_str in dates:
        target_date = pd.to_datetime(d_str, format='%Y-%m-%d', errors='coerce')
        if pd.isna(target_date):
            # If the date string can't be parsed, skip
            continue
        
        # Match the exact date
        row = data[data['Date'] == target_date]
        if not row.empty:
            row = row.iloc[0]  # Get the first matching row
            indicators[d_str] = {
                "EMA10": row.get("EMA_10", None),
                "EMA20": row.get("EMA_20", None),
                "EMA50": row.get("EMA_50", None),
                "EMA100": row.get("EMA_100", None),
                "EMA200": row.get("EMA_200", None),
                "MACD_2day": row.get("MACD_Histogram", None),
                "MACD_1day": row.get("MACD_Line", None),
                "RSI_1day": row.get("RSI", None),
            }

    return indicators

def load_trading_data(sheet_url):
    """
    Load trading data from a Google Sheet and preprocess it.
    
    Parameters:
        sheet_url (str): URL of the Google Sheet containing trading data
    
    Returns:
        pandas.DataFrame: Processed trading data
    """
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 
                  'https://www.googleapis.com/auth/drive']
        
        credentials = Credentials.from_service_account_file(
            r"C:\Users\Reio\Desktop\Folderid\Proge\Projektid\Stock analysis\fourth-gantry-443708-n2-48cba6184af8.json", 
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.sheet1  # Assuming data is in the first sheet
        
        all_values = worksheet.get_all_values()

        headers = all_values[0]
        data_rows = all_values[1:]

        data = pd.DataFrame(data_rows, columns=headers)

        data['Date'] = pd.to_datetime(data['Date'], dayfirst=True, errors='coerce')
        
        # Filter data from 01.01.2023
        data = data[data['Date'] >= '2023-01-01']
        
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        data.fillna(method='ffill', inplace=True)
        
        data.sort_values('Date', inplace=True, ignore_index=True)
        
        return data
    except Exception:
        return None

def calculate_indicators(data, close_column='Close'):
    """
    Calculate comprehensive technical indicators for the given DataFrame.
    
    Parameters:
        data (pandas.DataFrame): Input trading data
        close_column (str): Name of the column to use for close prices
    
    Returns:
        pandas.DataFrame: DataFrame with added technical indicators
    """
    df = data.copy()
    
    # SMA
    sma_windows = [3, 5, 10, 20, 50, 100, 200]
    for window in sma_windows:
        df[f'SMA_{window}'] = df[close_column].rolling(window=window).mean()
    
    # EMA
    ema_windows = [3, 5, 10, 20, 50, 100, 200]
    for window in ema_windows:
        df[f'EMA_{window}'] = df[close_column].ewm(span=window, adjust=False).mean()
    
    # MACD
    df['EMA_12'] = df[close_column].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df[close_column].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD_Line'] - df['MACD_Signal']
    
    # RSI
    delta = df[close_column].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)

    ma_up = up.ewm(com=14-1, adjust=True, min_periods=14).mean()
    ma_down = down.ewm(com=14-1, adjust=True, min_periods=14).mean()
    rs = ma_up / ma_down
    df['RSI'] = 100.0 - (100.0 / (1.0 + rs))
    
    return df

def get_trading_signals(df):
    """
    Generate trading signals based on technical indicators.
    
    Parameters:
        df (pandas.DataFrame): DataFrame with technical indicators
    
    Returns:
        dict: Dictionary of trading signals and conditions
    """
    signals = {}
    last_row = df.iloc[-1]
    
    # SMA Signals
    signals['sma_10_above_20'] = last_row['SMA_10'] > last_row['SMA_20']
    signals['sma_20_above_50'] = last_row['SMA_20'] > last_row['SMA_50']
    signals['sma_50_above_100'] = last_row['SMA_50'] > last_row['SMA_100']
    signals['sma_100_above_200'] = last_row['SMA_100'] > last_row['SMA_200']
    
    # EMA Signals
    signals['ema_10_above_20'] = last_row['EMA_10'] > last_row['EMA_20']
    signals['ema_20_above_50'] = last_row['EMA_20'] > last_row['EMA_50']
    signals['ema_50_above_100'] = last_row['EMA_50'] > last_row['EMA_100']
    signals['ema_100_above_200'] = last_row['EMA_100'] > last_row['EMA_200']
    
    # MACD Signals
    signals['macd_above_signal'] = last_row['MACD_Line'] > last_row['MACD_Signal']
    signals['macd_positive'] = last_row['MACD_Line'] > 0
    
    # RSI Signals
    signals['rsi_oversold'] = last_row['RSI'] < 30
    signals['rsi_overbought'] = last_row['RSI'] > 70
    
    # Price vs Moving Averages
    signals['price_above_sma_50'] = last_row['Close'] > last_row['SMA_50']
    signals['price_above_ema_50'] = last_row['Close'] > last_row['EMA_50']
    
    # Crossover Signals (need at least 2 rows)
    if len(df) > 1:
        prev_row = df.iloc[-2]
        signals['sma_golden_cross'] = (last_row['SMA_50'] > last_row['SMA_200']) and (prev_row['SMA_50'] <= prev_row['SMA_200'])
        signals['sma_death_cross'] = (last_row['SMA_50'] < last_row['SMA_200']) and (prev_row['SMA_50'] >= prev_row['SMA_200'])
        signals['ema_golden_cross'] = (last_row['EMA_50'] > last_row['EMA_200']) and (prev_row['EMA_50'] <= prev_row['EMA_200'])
        signals['ema_death_cross'] = (last_row['EMA_50'] < last_row['EMA_200']) and (prev_row['EMA_50'] >= prev_row['EMA_200'])
    else:
        signals['sma_golden_cross'] = False
        signals['sma_death_cross'] = False
        signals['ema_golden_cross'] = False
        signals['ema_death_cross'] = False
    
    return signals

def main(sheet_url):
    """
    Main function to calculate technical indicators.
    
    Parameters:
        sheet_url (str): URL of the Google Sheet
    
    Returns:
        tuple: Processed DataFrame and trading signals
    """
    data = load_trading_data(sheet_url)
    
    if data is not None:
        # Calculate indicators once here, so subsequent calls to calculate_indicators_for_dates won't recalc
        df_with_indicators = calculate_indicators(data)
        signals = get_trading_signals(df_with_indicators)
        return df_with_indicators, signals
    else:
        return None, None

if __name__ == "__main__":
    sheet_url = "https://docs.google.com/spreadsheets/d/17og3NaMOTc0DFJQ1FmOA91DUHbUc9STBiPuZ0GYlX1g/edit?gid=699528986#gid=699528986"
    main(sheet_url)
