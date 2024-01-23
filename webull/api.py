from .endpoints import Endpoints
import pkgutil
import yaml
import uuid
from email_validator import validate_email, EmailNotValidError
import requests
import hashlib
import pandas as pd
import pytz
from datetime import datetime, timedelta
import time


class Api:
    def __init__(self, did):
        self._did = did

        self._urls = Endpoints()

        self._info = yaml.safe_load(pkgutil.get_data(__name__, "info.yaml"))
        self._BASE_HEADERS = self._info["base_headers"]
        self._region_code = self._info["region_code"]
        self._zone_var: self._info["zone_var"]

    def build_headers(
        self,
        access_token=None,
        trade_token=None,
        include_time=False,
        include_zone_var=False,
    ):
        headers = self._BASE_HEADERS
        headers["reqid"] = str(uuid.uuid4().hex)
        headers["did"] = self._did
        if access_token:
            headers["access_token"] = access_token
        if trade_token:
            headers["t_token"] = trade_token
        if include_time:
            headers["t_time"] = str(time.time() * 1000)

        headers = dict(sorted(headers.items(), key=lambda k: k[0].casefold()))

        return headers

    def _get_account_type(self, username):
        try:
            validate_email(username)
            account_type = 2
        except EmailNotValidError:
            account_type = 1

        return account_type

    def get_auth_tokens(
        self, username, password, mfa_code=None, security_question_id=None, answer=None
    ):
        headers = self.build_headers()

        password = ("wl_app-a&b@!423^" + password).encode("utf-8")
        md5_hash = hashlib.md5(password)

        account_type = self._get_account_type(username)

        data = {
            "account": username,
            "accountType": account_type,
            "pwd": md5_hash.hexdigest(),
            "deviceId": self._did,
            "deviceName": "Bot Simpson",
            "grade": 1,
            "regionId": self._region_code,
        }

        if mfa_code is not None:
            data["extInfo"] = {
                "codeAccountType": account_type,
                "verificationCode": mfa_code,
            }

        if security_question_id is not None and answer is not None:
            data["accessQuestions"] = (
                '[{"questionId":"'
                + str(security_question_id)
                + '", "answer":"'
                + str(answer)
                + '"}]'
            )

        response = requests.post(self._urls.get_tokens, json=data, headers=headers)

        result = response.json()

        if "accessToken" in result.keys():
            self._access_token = result["accessToken"]
            self._refresh_token = result["refreshToken"]
            dict = {
                k: v
                for k, v in result.items()
                if k in ["accessToken", "refreshToken", "tokenExpireTime"]
            }
            dict["success"] = True
            return dict
        elif result["code"] == "account.pwd.mismatch":
            return {"error_msg": result["msg"], "success": False}
        elif "extInfo" in result.keys():
            return {"error_msg": "MFA Activated", "success": False}

    def refresh_tokens(self, access_token, refresh_token):
        headers = self.build_headers(access_token=access_token)

        data = {"refreshToken": refresh_token}

        response = requests.post(
            self._urls.refresh_tokens + refresh_token, json=data, headers=headers
        )

        result = response.json()

        if "accessToken" in result.keys():
            self._access_token = result["accessToken"]
            self._refresh_token = result["refreshToken"]
            return result
        else:
            raise ValueError("Error Refreshing Tokens")

    def get_trade_token(self, trade_pin):
        headers = self.build_headers(access_token=self._access_token)

        trade_pin = ("wl_app-a&b@!423^" + str(trade_pin)).encode("utf-8")
        md5_hash = hashlib.md5(trade_pin)
        data = {"pwd": md5_hash.hexdigest()}

        response = requests.post(self._urls.trade_token, json=data, headers=headers)
        result = response.json()

        if "tradeToken" in result.keys():
            self._trade_token = result["tradeToken"]
            return result["tradeToken"]
        else:
            return ValueError("Error Getting Trade Token")

    def get_account_id(self):
        headers = self.build_headers(access_token=self._access_token)

        response = requests.get(self._urls.account_id, headers=headers)
        result = response.json()

        if result["success"] and len(result["data"]) > 0:
            self._account_id = str(result["data"][0]["secAccountId"])
            return self._account_id
        else:
            return None

    def get_account(self):
        headers = self.build_headers(access_token=self._access_token)
        response = requests.get(self._urls.account + self._account_id, headers=headers)
        result = response.json()
        return result

    def get_positions(self):
        return self.get_account()["positions"]

    def get_portfolio(self):
        data = self.get_account()
        dict = {}
        for item in data["accountMembers"]:
            dict[item["key"]] = item["value"]
        return dict

    def get_order_history(self, status="All", count=20):
        headers = self.build_headers(trade_token=self._trade_token, include_time=True)
        response = requests.get(
            self._urls.order_history(self._account_id, count) + str(status),
            headers=headers,
        )
        return response.json()

    def get_ticker_id(self, ticker):
        headers = self.build_headers()

        params = {
            "keyword": ticker.upper(),
            "pageIndex": 1,
            "pageSize": 20,
            "regionId": self._region_code,
        }
        if ticker and isinstance(ticker, str):
            response = requests.get(
                self._urls.ticker_id, headers=headers, params=params
            )
            result = response.json()

            if result.get("data"):
                for item in result["data"]:
                    if "symbol" in item and item["symbol"] == ticker:
                        ticker_id = item["tickerId"]
                        break
                    elif "disSymbol" in item and item["disSymbol"] == ticker:
                        ticker_id = item["tickerId"]
                        break
                    else:
                        raise ValueError("Invalid Ticker")
            else:
                raise ValueError(f"Ticker ID could not be found for {ticker}")

        else:
            raise ValueError("Must provide a ticker as string")

        return ticker_id

    def get_quote(self, ticker=None, ticker_id=None):
        headers = self.build_headers()
        if ticker:
            ticker_id = self.get_ticker_id(ticker)
        elif not ticker_id:
            raise ValueError("Must provide a ticker or ticker ID")

        params = {"tickerId": ticker_id, "includeSecu": 1, "includeQuote": 1}

        response = requests.get(self._urls.quote, params=params, headers=headers)
        result = response.json()

        return result

    def get_ohlc(
        self,
        ticker=None,
        ticker_id=None,
        interval="w1",
        count=100,
        end_date=None,
        extended_trading=0,
    ):
        headers = self.build_headers()

        if ticker:
            ticker_id = self.get_ticker_id(ticker)
        elif not ticker_id:
            raise ValueError("Must provide a ticker or ticker ID")

        if interval.lower() in ["m1", "1m", "m", "1min", "min", "minute"]:
            interval = "m1"
        elif interval.lower() in ["m5", "5m", "5min"]:
            interval = "m5"
        elif interval.lower() in ["m10", "10m", "10min"]:
            interval = "m10"
        elif interval.lower() in ["m15", "15m", "15min"]:
            interval = "m15"
        elif interval.lower() in ["m30", "30m", "30min"]:
            interval = "m30"
        elif interval.lower() in ["h1", "1h", "1hr", "hr", "1hour", "hour"]:
            interval = "m60"
        elif interval.lower() in ["h2", "2h", "2hr", "2hour"]:
            interval = "h2"
        elif interval.lower() in ["h4", "4h", "4hr", "4hour"]:
            interval = "h4"
        elif interval.lower() in ["d1", "1d", "d", "1day", "day"]:
            interval = "d1"
        elif interval.lower() in ["w1", "w", "wk", "1wk", "week"]:
            inverval = "w1"
        elif interval.lower() in ["mth1", "mth", "month", "1month"]:
            interval = "mth1"
        elif interval.lower() in ["mth3", "3month", "q", "quarter"]:
            interval = "mth3"
        elif interval.lower() in ["y1", "1y", "y", "year", "yr", "1yr"]:
            interval = "y1"

        params = {"tickerIds": ticker_id, "type": interval, "count": count}
        if extended_trading in [1, True]:
            params["extendTrading"] = 1
        elif extended_trading in [0, False]:
            params["extendTrading"] = 0
        if end_date:
            params["timestamp"] = int(datetime.fromisoformat(end_date).timestamp())
        response = requests.get(self._urls.ohlc, headers=headers, params=params)
        result = response.json()

        timezone = pytz.timezone(result[0]["timeZone"])

        data = result[0]["data"]
        for idx, row in enumerate(data):
            data[idx] = row.split(",")

        df = pd.DataFrame(
            data,
            columns=[
                "close_date",
                "open",
                "close",
                "high",
                "low",
                "prev_close",
                "volume",
                "vwap",
            ],
        )
        df["close_date"] = (
            pd.to_datetime(df.close_date, unit="s")
            .dt.tz_localize("UTC")
            .dt.tz_convert(timezone)
        )
        df = df.replace("null", None)
        df = df.astype(
            {
                "open": float,
                "close": float,
                "high": float,
                "low": float,
                "prev_close": float,
                "volume": float,
                "vwap": float,
            }
        )

        # close_dates = []
        # opens = []
        # highs = []
        # lows = []
        # closes = []
        # volumes = []
        # for row in result[0]['data']:
        #     row = row.split(",")
        #     close_date = (
        #         datetime.fromtimestamp(int(row[0]))
        #         .astimezone(timezone)
        #     )
        #     close_dates.append(close_date)
        #     opens.append(float(row[1]))
        #     closes.append(float(row[2]))
        #     highs.append(float(row[3]))
        #     lows.append(float(row[4]))
        #     volumes.append(float(row[6]))

        # dict = {
        #     "close_date": close_dates,
        #     "open": opens,
        #     "high": highs,
        #     "low": lows,
        #     "close": closes,
        #     "volume": volumes,
        # }

        # df = pd.DataFrame(dict)
        df = df.sort_values("close_date").reset_index(drop=True)
        df = df[
            [
                "close_date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        ]

        df = df.dropna()

        return df

    def place_single_order(
        self,
        ticker,
        action,
        quantity,
        order_type,
        time_in_force,
        extended_hours=False,
        lmt_price=None,
    ):
        headers = self.build_headers(
            access_token=self._access_token,
            trade_token=self._trade_token,
            include_time=True,
        )

        data = {
            "action": action,
            "comboType": "NORMAL",
            "orderType": order_type,
            "outsideRegularTradingHour": extended_hours,
            "quantity": round(quantity, 5),
            "serialId": str(uuid.uuid4()),
            "tickerId": self.get_ticker_id(ticker),
            "timeInForce": time_in_force,
        }

        if order_type == "MKT":
            data["outsideRegularTradingHour"] = False
        elif order_type == "LMT":
            data["lmtPrice"] = float(lmt_price)

        url = f"https://ustrade.webullfinance.com/api/trade/order/{self._account_id}/placeStockOrder"

        response = requests.post(
            self._urls.place_single_order(self._account_id), json=data, headers=headers
        )
        result = response.json()

        return result

    def place_combo_order(
        self,
        ticker,
        action,
        quantity,
        order_type,
        time_in_force,
        stop_loss=None,
        stop_gain=None,
        extended_hours=False,
    ):
        if not stop_loss and not stop_gain:
            raise ValueError("Must Input Stop Loss or Stop Gain")

        quote = float(self.get_quote(ticker)["close"])

        headers = self.build_headers(
            access_token=self._access_token,
            trade_token=self._trade_token,
            include_time=True,
        )

        data = {
            "newOrders": [
                {
                    "orderType": order_type,
                    "timeInForce": time_in_force,
                    "quantity": quantity,
                    "outsideRegularTradingHour": extended_hours,
                    "action": action,
                    "tickerId": self.get_ticker_id(ticker),
                    "comboType": "MASTER",
                },
            ]
        }

        if stop_loss:
            stop_price = round(quote * (1 - stop_loss), 2)

            stop_order = {
                "orderType": "STP",
                "timeInForce": "GTC",
                "quantity": quantity,
                "outsideRegularTradingHour": False,
                "action": "SELL",
                "tickerId": self.get_ticker_id(ticker),
                "auxPrice": stop_price,
                "comboType": "STOP_LOSS",
            }
            data["newOrders"].append(stop_order)

        if stop_gain:
            stop_price = round(quote * (1 + stop_gain), 2)
            print(quote, stop_price)
            stop_order = {
                "orderType": "LMT",
                "timeInForce": "GTC",
                "quantity": quantity,
                "outsideRegularTradingHour": False,
                "action": "SELL",
                "tickerId": self.get_ticker_id(ticker),
                "lmtPrice": stop_price,
                "comboType": "STOP_PROFIT",
            }
            data["newOrders"].append(stop_order)

        url = f"https://ustrade.webullfinance.com/api/trade/v2/corder/stock/check/{account_id}"

        response = requests.post(url, json=data, headers=headers)

        result = response.json()

        if result["forward"]:
            for order in data["newOrders"]:
                order["serialId"] = str(uuid.uuid4())

            url = f"https://ustrade.webullfinance.com/api/trade/v2/corder/stock/place/{account_id}"

            response = requests.post(url, json=data, headers=headers)
            result = response.json()
            return result
        else:
            print(result["checkResultList"][0]["msg"])
