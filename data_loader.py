import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def authenticate_google_sheet(credentials_path, scopes):
    """
    Authenticate the client for accessing Google Sheets.
    """
    try:
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate Google Sheets: {e}")

def fetch_sheet_data(client, sheet_url, sheet_name):
    """
    Fetch raw data from a Google Sheet.
    """
    try:
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(sheet_name)
        return worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data from Google Sheet: {e}")

def preprocess_data(raw_data, is_intraday=False):
    """
    Preprocess raw data into a pandas DataFrame.
    Handles both daily and intraday data.
    """
    try:
        if not raw_data:
            raise RuntimeError("No data found in the sheet.")

        # Identify header row
        header_row_index = None
        for i, row in enumerate(raw_data):
            if "Date" in row and "Open" in row:
                header_row_index = i
                break

        if header_row_index is None:
            raise RuntimeError("The header row could not be found.")

        # Create DataFrame
        headers = raw_data[header_row_index]
        data_rows = raw_data[header_row_index + 1:]
        data = pd.DataFrame(data_rows, columns=headers)

        # Clean up column names
        data.columns = data.columns.str.strip()

        # Convert 'Date' column to datetime
        data['Date'] = pd.to_datetime(data['Date'], dayfirst=True, errors='coerce')

        # Ensure 'Index' column (S&P500 return) is numeric
        if 'Index' in data.columns:
            data['Index'] = pd.to_numeric(data['Index'], errors='coerce')
        
        # If intraday, parse time and create 'Datetime'
        if is_intraday and 'Time' in data.columns:
            data['Time'] = pd.to_datetime(data['Time'], format='%H:%M', errors='coerce').dt.time
            data['Datetime'] = pd.to_datetime(data['Date'].astype(str) + ' ' + data['Time'].astype(str))
            data.drop(columns=['Date', 'Time'], inplace=True)

            data.sort_values(by='Datetime', inplace=True)
            data.reset_index(drop=True, inplace=True)

        # Convert numeric columns
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

        # Fill missing data
        data.fillna(0, inplace=True)

        # Optional Average Price
        if 'High' in data.columns and 'Low' in data.columns:
            data['Average Price'] = (data['High'] + data['Low']) / 2

        return data

    except Exception as e:
        raise RuntimeError(f"Failed to preprocess data: {e}")

def load_data(sheet_url, credentials_path, daily_sheet="Sheet1", intraday_sheet=None):
    """
    1) Load daily data from 'daily_sheet' (e.g. "Sheet1") and
       retrieve the stock ticker from the 'Stock' column (first row).
    2) If intraday_sheet is specified, load intraday data from that sheet name.

    Returns:
        (daily_data, intraday_data, ticker)
    """
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    client = authenticate_google_sheet(credentials_path, scopes)

    # 1) Fetch daily data
    raw_daily_data = fetch_sheet_data(client, sheet_url, daily_sheet)
    daily_data = preprocess_data(raw_daily_data, is_intraday=False) if raw_daily_data else None

    # Extract ticker from the daily data's 'Stock' column (assuming the first row is correct)
    ticker = None
    if daily_data is not None and 'Stock' in daily_data.columns:
        non_na_stocks = daily_data['Stock'].dropna()
        if not non_na_stocks.empty:
            ticker = non_na_stocks.iloc[0]  # e.g. "AAPL"

    # 2) Fetch intraday data (if intraday_sheet provided)
    if intraday_sheet:
        raw_intraday_data = fetch_sheet_data(client, sheet_url, intraday_sheet)
        intraday_data = preprocess_data(raw_intraday_data, is_intraday=True) if raw_intraday_data else None
    else:
        intraday_data = None

    return daily_data, intraday_data, ticker
