from dataclasses import dataclass


@dataclass(frozen=True)
class Ticker:
    symbol: str
    price: float


@dataclass(frozen=True)
class Candle:
    ts: int
    o: float
    hi: float
    lo: float
    c: float
    v: float
