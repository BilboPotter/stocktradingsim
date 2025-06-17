import datetime
import os
import pandas as pd
import json
import re
from websocket import create_connection
import random
import string
import gspread
from google.oauth2.service_account import Credentials

class Interval:
    min_30 = "30"

class TradingViewData:
    __ws_headers = json.dumps({"Origin": "https://data.tradingview.com"})
    __ws_timeout = 5

    def __init__(self) -> None:
        self.ws = None
        self.session = self.__generate_session()
        self.chart_session = self.__generate_chart_session()

    @staticmethod
    def __generate_session():
        return "qs_" + ''.join(random.choices(string.ascii_lowercase, k=12))

    @staticmethod
    def __generate_chart_session():
        return "cs_" + ''.join(random.choices(string.ascii_lowercase, k=12))

    def __create_connection(self):
        self.ws = create_connection(
            "wss://data.tradingview.com/socket.io/websocket", 
            headers=self.__ws_headers, 
            timeout=self.__ws_timeout
        )

    def __send_message(self, func, args):
        message = json.dumps({"m": func, "p": args}, separators=(",", ":"))
        self.ws.send(f"~m~{len(message)}~m~{message}")

    @staticmethod
    def __create_df(raw_data, symbol):
        try:
            out = re.search(r'"s":\[(.+?)\}\]', raw_data).group(1)
            x = out.split(r',{"')
            data = []

            for xi in x:
                xi = re.split(r"\[|:|,|\]", xi)
                ts = datetime.datetime.fromtimestamp(float(xi[4]))
                row = [ts] + [float(xi[i]) for i in range(5, 10)]
                data.append(row)

            df = pd.DataFrame(data, columns=["datetime", "open", "high", "low", "close", "volume"])
            df.insert(0, "symbol", symbol)
            return df
        except AttributeError:
            print("No data available. Please check the exchange and symbol.")
            return pd.DataFrame()

    def get_hist(self, symbol, exchange, start_date, interval=Interval.min_30):
        self.__create_connection()
        self.__send_message("chart_create_session", [self.chart_session, ""])
        self.__send_message("resolve_symbol", [
            self.chart_session, "symbol_1", f'={{"symbol":"{exchange}:{symbol}"}}'
        ])

        n_bars = self.__calculate_bars(start_date)
        self.__send_message("create_series", [
            self.chart_session, "s1", "s1", "symbol_1", interval, n_bars
        ])

        raw_data = ""
        while True:
            try:
                result = self.ws.recv()
                raw_data += result + "\n"
                if "series_completed" in result:
                    break
            except Exception:
                break

        return self.__create_df(raw_data, symbol)

    @staticmethod
    def __calculate_bars(start_date):
        now = datetime.datetime.now()
        trading_hours = 6.5
        bars_per_day = trading_hours * 2
        days = (now - start_date).days
        return int(days * bars_per_day)

    def save_to_google_sheets(self, data, ticker, sheet_url, credentials_path):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(sheet_url)
        worksheet_name = f"{ticker}30"
        try:
            worksheet = sheet.worksheet(worksheet_name)
            sheet.del_worksheet(worksheet)
        except gspread.exceptions.WorksheetNotFound:
            pass
        worksheet = sheet.add_worksheet(title=worksheet_name, rows=str(len(data) + 1), cols="7")

        # Reformat datetime and reorder columns
        data['date'] = data['datetime'].dt.strftime('%d/%m/%Y')
        data['time'] = data['datetime'].dt.strftime('%H:%M')
        data = data[['date', 'time', 'open', 'high', 'low', 'close', 'volume']]  # Correct column order

        worksheet.append_row(["Date", "Time", "Open", "High", "Low", "Close", "Volume"])
        worksheet.insert_rows(data.values.tolist(), 2)

if __name__ == "__main__":
    SHEET_URL = "google sheets url"
    CREDENTIALS_PATH = r"fourth-gantry file"
    
    tv = TradingViewData()
    start_date = datetime.datetime(2024, 1, 1)
    ticker = "VRT"
    data = tv.get_hist(ticker, "NYSE", start_date)

    if not data.empty:
        tv.save_to_google_sheets(data, ticker, SHEET_URL, CREDENTIALS_PATH)
        print(f"Data for {ticker} saved to Google Sheets.")
    else:
        print("No data to save.")
