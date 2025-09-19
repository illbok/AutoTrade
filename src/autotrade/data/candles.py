from typing import Iterable
from autotrade.exchanges.base import IExchangeClient
from autotrade.models.market import Candle

class CandleService:
    def __init__(self, exchange: IExchangeClient):
        self.exchange = exchange

    def fetch(self, symbol: str, interval: str, window: int) -> Iterable[Candle]:
        return self.exchange.get_candles(symbol, interval, limit=window)
