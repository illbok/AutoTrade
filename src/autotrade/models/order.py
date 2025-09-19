from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str   # "buy" | "sell"
    qty: float
    type: str = "market"

    @classmethod
    def market(cls, symbol: str, side: str, qty: float):
        return cls(symbol=symbol, side=side, qty=qty, type="market")

@dataclass(frozen=True)
class Order:
    id: str
    symbol: str
    side: str
    qty: float
    price: Optional[float] = None
