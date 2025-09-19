from typing import Protocol, Iterable
from autotrade.models.market import Candle
from autotrade.models.order import OrderRequest

class IStrategy(Protocol):
    name: str
    symbols: list[str]
    def on_start(self) -> None: ...
    def generate(self, candles: dict[str, Iterable[Candle]]) -> list[OrderRequest]: ...
    