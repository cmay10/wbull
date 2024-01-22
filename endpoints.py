class Endpoints:
  BASE_STOCK_INFO_URL = 'https://quotes-gw.webullbroker.com/api'
  BASE_USER_URL = 'https://userapi.webull.com/api'
#   BASE_USER_URL = 'https://u1suser.webullfintech.com/api'
  BASE_USER_MFA_URL = 'https://userapi.webullfintech.com/api'
  BASE_ACCOUNT_URL = 'https://tradeapi.webullbroker.com/api/trade'
  BASE_TRADE_URL = 'https://ustrade.webullfinance.com/api'

  @property
  def get_tokens(self):
    return 'https://userapi.webull.com/api/passport/login/v5/account'

  @property
  def refresh_tokens(self):
    return 'https://userapi.webull.com/api/passport/refreshToken?refreshToken='

  @property
  def trade_token(self):
    return 'https://trade.webullfintech.com/api/trading/v1/global/trade/login'

  @property
  def account_id(self):
    return 'https://tradeapi.webullbroker.com/api/trade/account/getSecAccountList/v5'

  @property
  def account(self):
    return 'https://tradeapi.webullbroker.com/api/trade/v3/home/'

  def order_history(self,account_id,page_size):
    return f'https://ustrade.webullbroker.com/api/trade/v2/option/list?secAccountId={account_id}&startTime=1970-0-1&dateType=ORDER&pageSize={page_size}&status='

  @property
  def ticker_id(self):
    return 'https://quotes-gw.webullbroker.com/api/search/pc/tickers'

  @property
  def quote(self):
    return 'https://quotes-gw.webullbroker.com/api/quotes/ticker/getTickerRealTime'

  @property
  def ohlc(self):
    return 'https://quotes-gw.webullfintech.com/api/quote/charts/query'

  def place_single_order(self,account_id):
    return f'https://ustrade.webullfinance.com/api/trade/order/{account_id}/placeStockOrder'