import random, time
from typing import Iterable, List
from autotrade.exchanges.base import IExchangeClient
from autotrade.models.market import Ticker, Candle
from autotrade.models.order import OrderRequest, Order

class FakeExchange(IExchangeClient):
    name = "fake"

    def __init__(self, seed: int = 42, base_price: float = 30000.0):
        random.seed(seed)
        self._p = base_price
        self._order_seq = 0

    def _step(self):
        self._p *= (1.0 + random.uniform(-0.001, 0.001))
        return self._p

    def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(symbol, self._step())

    def get_candles(self, symbol: str, interval: str, limit: int = 60) -> Iterable[Candle]:
        out: List[Candle] = []
        ts = int(time.time()) - limit * 60
        p = self._p
        for _ in range(limit):
            p *= (1.0 + random.uniform(-0.002, 0.002))
            h = p * (1 + random.uniform(0, 0.001))
            l = p * (1 - random.uniform(0, 0.001))
            c = p
            o = (h + l) / 2
            v = random.uniform(1, 10)
            ts += 60
            out.append(Candle(ts, o, h, l, c, v))
        return out

    def create_order(self, req: OrderRequest) -> Order:
        self._order_seq += 1
        price = self._step()
        return Order(id=f"F{self._order_seq}", symbol=req.symbol, side=req.side, qty=req.qty, price=price)
