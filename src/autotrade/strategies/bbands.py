# src/autotrade/strategies/bbands.py
# ------------------------------------------------------------
# Bollinger Bands 전략: SMA ± k*std 밴드 돌파/복귀 교차로 신호 생성
# ------------------------------------------------------------
from __future__ import annotations
from typing import Iterable, List, Dict
from collections import deque
from typing import Deque
from math import sqrt
from autotrade.models.market import Candle
from autotrade.models.order import OrderRequest
from autotrade.strategies.registry import register


def _sma(values: List[float], window: int) -> List[float]:
    out: List[float] = []
    if window <= 0:
        return out
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= window:
            s -= values[i - window]
        out.append(s / window if i + 1 >= window else float("nan"))
    return out


def _rolling_std(values: List[float], window: int) -> List[float]:
    # Welford라기보단 간단 이동표준편차 (성능 OK)
    out: List[float] = []
    if window <= 1:
        return [float("nan")] * len(values)

    q: Deque[float] = deque()
    s1 = 0.0
    s2 = 0.0
    for i, v in enumerate(values):
        q.append(v)
        s1 += v
        s2 += v * v
        if len(q) > window:
            old = q.popleft()
            s1 -= old
            s2 -= old * old
        if len(q) == window:
            mean = s1 / window
            var = max(s2 / window - mean * mean, 0.0)
            out.append(sqrt(var))
        else:
            out.append(float("nan"))
    return out


@register("bbands")
class BBandsStrategy:
    """
    파라미터:
      window: int = 20
      k: float = 2.0              # 밴드 폭
      mode: str = "breakout"      # "breakout" | "revert"
      use_crossover: bool = True  # 밴드 '처음' 돌파(복귀)만 신호
      cooldown: int = 0
      qty: float = 0.001
    """

    def __init__(
        self,
        symbols: list[str],
        window: int = 20,
        k: float = 2.0,
        mode: str = "breakout",
        use_crossover: bool = True,
        cooldown: int = 0,
        qty: float = 0.001,
    ):
        assert mode in ("breakout", "revert")
        self.name = "bbands"
        self.symbols = symbols
        self.window = window
        self.k = k
        self.mode = mode
        self.use_crossover = use_crossover
        self.cooldown = cooldown
        self.qty = qty

    def on_start(self) -> None:
        pass

    def _signals(self, closes: List[float]) -> List[int]:
        sma = _sma(closes, self.window)
        std = _rolling_std(closes, self.window)
        n = len(closes)
        sig = [0] * n
        if n < self.window + 2:
            return sig

        upper = [
            m + self.k * s if (m == m and s == s) else float("nan")
            for m, s in zip(sma, std)
        ]
        lower = [
            m - self.k * s if (m == m and s == s) else float("nan")
            for m, s in zip(sma, std)
        ]

        if self.mode == "breakout":
            # 상단 돌파=매수, 하단 돌파=매도 (추세 추종)
            if self.use_crossover:
                for i in range(1, n):
                    c0, c1 = closes[i - 1], closes[i]
                    up0, up1 = upper[i - 1], upper[i]
                    lo0, lo1 = lower[i - 1], lower[i]
                    if up0 == up0 and up1 == up1 and c0 <= up0 and c1 > up1:
                        sig[i] = 1
                    elif lo0 == lo0 and lo1 == lo1 and c0 >= lo0 and c1 < lo1:
                        sig[i] = -1
            else:
                for i in range(n):
                    if upper[i] == upper[i] and closes[i] > upper[i]:
                        sig[i] = 1
                    elif lower[i] == lower[i] and closes[i] < lower[i]:
                        sig[i] = -1
        else:
            # revert(평균회귀): 상단 밴드 복귀=매도, 하단 밴드 복귀=매수
            if self.use_crossover:
                for i in range(1, n):
                    c0, c1 = closes[i - 1], closes[i]
                    up0, up1 = upper[i - 1], upper[i]
                    lo0, lo1 = lower[i - 1], lower[i]
                    if up0 == up0 and up1 == up1 and c0 >= up0 and c1 < up1:
                        sig[i] = -1
                    elif lo0 == lo0 and lo1 == lo1 and c0 <= lo0 and c1 > lo1:
                        sig[i] = 1
            else:
                for i in range(n):
                    if (
                        upper[i] == upper[i]
                        and closes[i] < upper[i]
                        and closes[i - 1] >= upper[i - 1]
                    ):
                        sig[i] = -1
                    elif (
                        lower[i] == lower[i]
                        and closes[i] > lower[i]
                        and closes[i - 1] <= lower[i - 1]
                    ):
                        sig[i] = 1

        if self.cooldown > 0:
            cd = self.cooldown
            last = -(10**9)
            for i in range(n):
                if sig[i] != 0:
                    last = i
                elif i - last <= cd:
                    sig[i] = 0
        return sig

    def generate(self, candles: Dict[str, Iterable[Candle]]) -> List[OrderRequest]:
        orders: List[OrderRequest] = []
        for sym in self.symbols:
            cs = list(candles.get(sym, []))
            if not cs:
                continue
            closes = [c.c for c in cs]
            sig = self._signals(closes)
            if sig and sig[-1] == 1:
                orders.append(OrderRequest.market(sym, "buy", self.qty))
            elif sig and sig[-1] == -1:
                orders.append(OrderRequest.market(sym, "sell", self.qty))
        return orders
