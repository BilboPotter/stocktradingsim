import gspread
from google.oauth2.service_account import Credentials
#from datetime import timedelta
import pandas as pd
from datetime import datetime

# Configuration
CREDENTIALS_PATH = r"fourth-gantry"
OUTPUT_SHEET_URL = "Sheet url"

def append_trades_to_sheet(trades, full_data_with_indicators, sheet_url=OUTPUT_SHEET_URL):
    """
    Append indicator data first, then add Pos, Ticker, and Return for trade-specific rows.

    Parameters:
        trades (dict): Dictionary of all trades and their details.
        indicators (pd.DataFrame): DataFrame of indicators including all necessary columns.
        sheet_url (str): URL of the Google Sheet where data will be written.
    """
    # Authenticate with Google Sheets
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 
              'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(credentials)

    # Open the Google Sheet
    sh = client.open_by_url(sheet_url)

    # Duplicate the template sheet
    template_ws = sh.worksheet("Template")
    template_sheet_id = template_ws.id
    new_sheet_name = f"Trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sh.batch_update({
        "requests": [{
            "duplicateSheet": {
                "sourceSheetId": template_sheet_id,
                "insertSheetIndex": 0,
                "newSheetName": new_sheet_name
            }
        }]
    })
    worksheet = sh.worksheet(new_sheet_name)

    # Step 1: Write All Indicator Data
    indicators = full_data_with_indicators[full_data_with_indicators['Date'] >= '2023-11-01'].copy()  # Filter and create a copy
    indicators['Date'] = indicators['Date'].dt.strftime('%d/%m/%Y')  # Format as DD/MM/YYYY


    headers = [
        "Date", "Pos", "Ticker", "Return", "SMA3", "SMA5", "SMA10", "SMA20", "SMA50",
        "EMA3", "EMA5", "EMA10", "EMA20", "EMA50", "EMA100", "RSI", "Close", "Open",
        "Low", "High", "Volume"
    ]
    worksheet.clear()
    worksheet.append_row(headers)

    rows_to_append = [
        [
            row["Date"], "", "", "", row.get("SMA_3", ""), row.get("SMA_5", ""),
            row.get("SMA_10", ""), row.get("SMA_20", ""), row.get("SMA_50", ""),
            row.get("EMA_3", ""), row.get("EMA_5", ""), row.get("EMA_10", ""),
            row.get("EMA_20", ""), row.get("EMA_50", ""), row.get("EMA_100", ""),
            row.get("RSI", ""), row["Close"], row["Open"], row["Low"], row["High"], row["Volume"]
        ]
        for _, row in indicators.iterrows()
    ]
    worksheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')

    # Step 2: Add Trades Data
    # Load back the written data to update with trades
    sheet_data = pd.DataFrame(worksheet.get_all_records())

    for pos, trade in trades.items():
        entry_date = trade.get("entry_date").strftime('%d/%m/%Y')
        ticker = trade.get("ticker", "")
        entry_price = trade.get("entry_price", 0)
        initial_amount = trade.get("initial_amount", 0)
        remaining_price = trade.get("remaining_price", entry_price)
        total_cost = entry_price * initial_amount
        final_value = remaining_price * initial_amount
        trade_return = ((final_value - total_cost) / total_cost) if total_cost else 0

        # Match row with the entry date
        row_index = sheet_data[sheet_data["Date"] == entry_date].index
        if not row_index.empty:
            row_idx = row_index[0]
            sheet_data.loc[row_idx, "Pos"] = pos
            sheet_data.loc[row_idx, "Ticker"] = ticker
            sheet_data.loc[row_idx, "Return"] = round(trade_return, 4)

    # Write updated trade data back to the sheet
    worksheet.clear()
    worksheet.append_row(headers)
    worksheet.append_rows(sheet_data.values.tolist(), value_input_option='USER_ENTERED')




def save_trade_data(trades, indicators):
    """
    Wrapper function to be called after final_summary.
    This function will create a new sheet from the Template and append all trades.
    """
    append_trades_to_sheet(trades, indicators)
