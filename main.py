from webull import Api
from datetime import datetime
import pandas as pd
import warnings

warnings.filterwarnings("ignore")
senate_transactions = pd.read_csv(
    "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.csv"
)
house_transactions = pd.read_csv(
    "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.csv"
)

senate_tickers = list(senate_transactions["ticker"].unique())
house_tickers = list(house_transactions["ticker"].unique())

tickers = list(set(senate_tickers + house_tickers))
tickers = sorted([str(t) for t in tickers])


did = "0294234787be44a4a5a90b883b0c8f15"
api = Api(did)

today = datetime.today().date()
first_date = datetime.fromisoformat("2014-01-01").date()

data = pd.DataFrame()
for i, ticker in enumerate(tickers[:9]):
    print(ticker, f"{i+1}/{len(tickers)}")
    ticker_data = pd.DataFrame()
    d = today
    while d >= first_date:
        try:
            df = api.get_ohlc(
                ticker=ticker, interval="d1", count=1200, end_date=d.isoformat()
            )

            d = df["close_date"].dt.date.values[0]

            ticker_data = pd.concat([ticker_data, df])
        except:
            with open("errors.txt", "a") as f:
                f.write(f"{ticker}\n")
            print(f"Could not get data for {ticker}")
            break

    if not ticker_data.empty:
        ticker_data["close_date"] = ticker_data.close_date.dt.round("1d").dt.date
        ticker_data = ticker_data.sort_values(by="close_date").drop_duplicates()
        ticker_data = ticker_data.set_index("close_date", drop=True)
        ticker_data.columns = pd.MultiIndex.from_product(
            [[ticker], ticker_data.columns]
        )

        if data.empty:
            data = ticker_data
        else:
            data = data.join(ticker_data, how="outer")

data.to_csv("data.csv")
data.to_parquet("data.parquet")
data.to_feather("data.feather")
