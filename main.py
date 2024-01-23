from webull import Api
from datetime import datetime
import pandas as pd
import warnings

warnings.filterwarnings("ignore")


sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
sp500["Symbol"] = sp500["Symbol"].str.replace(".","-",regex=False)
sp500 = sorted(list(sp500["Symbol"].values))

nasdaq100 = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[4]
nasdaq100["Ticker"] = nasdaq100["Ticker"].str.replace(".","-",regex=False)
nasdaq100 = sorted(list(nasdaq100["Ticker"].values))

tickers = sorted(list(set(nasdaq100 + sp500)))


did = "0294234787be44a4a5a90b883b0c8f15"
api = Api(did)

today = datetime.today().date()
first_date = datetime.fromisoformat("2010-01-01").date()

data = pd.DataFrame()
for i,ticker in enumerate(tickers):
    print(ticker,f"{i+1}/{len(tickers)}")
    ticker_data = pd.DataFrame()
    d = today
    while d >= first_date:
        try:
            df = api.get_ohlc(ticker=ticker, interval="m60", count=1200, end_date=d.isoformat())

            d = df["close_date"].dt.date.values[0]

            ticker_data = pd.concat([ticker_data,df])
        except:
            break
    
    ticker_data["close_date"] = ticker_data["close_date"].dt.round("30T")
    ticker_data = ticker_data.sort_values(by="close_date").drop_duplicates()
    ticker_data = ticker_data.set_index("close_date",drop=True)
    ticker_data[ticker] = ticker_data["close"]
    ticker_data = ticker_data[[ticker]]


    if data.empty:
        data = ticker_data
    else:
        data = data.join(ticker_data,how="outer")


data.to_csv("data.csv")

