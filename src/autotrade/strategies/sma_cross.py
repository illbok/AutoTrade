from typing import Iterable
from autotrade.strategies.base import IStrategy
from autotrade.strategies.registry import register
from autotrade.models.market import Candle
from autotrade.models.order import OrderRequest
from autotrade.analysis.indicators import sma

@register("sma_cross")
class SmaCross(IStrategy):
    def __init__(self, symbols, fast=5, slow=10):
        self.name = "sma_cross"
        self.symbols = symbols
        self.fast = fast
        self.slow = slow

    def on_start(self): pass

    def generate(self, candles: dict[str, Iterable[Candle]]):
        orders: list[OrderRequest] = []
        for sym in self.symbols:
            cs = list(candles[sym])
            closes = [c.c for c in cs]
            f = sma(closes, self.fast)
            s = sma(closes, self.slow)
            if len(closes) < self.slow + 1: 
                continue
            if f[-2] <= s[-2] and f[-1] > s[-1]:
                orders.append(OrderRequest.market(sym, "buy", 0.001))
            elif f[-2] >= s[-2] and f[-1] < s[-1]:
                orders.append(OrderRequest.market(sym, "sell", 0.001))
        return orders
