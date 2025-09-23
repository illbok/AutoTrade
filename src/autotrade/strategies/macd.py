# src/autotrade/strategies/macd.py
# ------------------------------------------------------------
# MACD 전략: EMA(fast/slow)와 Signal(ema of macd), Histogram 교차로 신호 생성
# - 입력: dict[str, Iterable[Candle]]
# - 출력: list[OrderRequest]
# - 마지막 캔들 신호만 주문으로 변환 (AutoTrade 표준)
# ------------------------------------------------------------
from __future__ import annotations
from typing import Iterable, List, Dict
from autotrade.models.market import Candle
from autotrade.models.order import OrderRequest
from autotrade.strategies.registry import register


def _ema(values: List[float], period: int) -> List[float]:
    if period <= 0 or not values:
        return []
    k = 2.0 / (period + 1)
    out: List[float] = []
    avg = 0.0
    for i, v in enumerate(values):
        if i == 0:
            avg = v
        else:
            avg = v * k + avg * (1 - k)
        out.append(avg)
    return out


@register("macd")
class MACDStrategy:
    """
    파라미터:
      fast: int = 12
      slow: int = 26
      signal: int = 9
      use_crossover: bool = True  # 히스토그램 0선 '처음' 교차만 신호
      cooldown: int = 0
      qty: float = 0.001
    """

    def __init__(
        self,
        symbols: list[str],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        use_crossover: bool = True,
        cooldown: int = 0,
        qty: float = 0.001,
    ):
        self.name = "macd"
        self.symbols = symbols
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.use_crossover = use_crossover
        self.cooldown = cooldown
        self.qty = qty

    def on_start(self) -> None:
        pass

    def _signals_from_hist(self, hist: List[float]) -> List[int]:
        n = len(hist)
        sig = [0] * n
        if n < 2:
            return sig
        if self.use_crossover:
            for i in range(1, n):
                a, b = hist[i - 1], hist[i]
                if a <= 0 and b > 0:
                    sig[i] = 1
                elif a >= 0 and b < 0:
                    sig[i] = -1
        else:
            for i, h in enumerate(hist):
                if h > 0:
                    sig[i] = 1
                elif h < 0:
                    sig[i] = -1

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
            if len(closes) < max(self.fast, self.slow, self.signal) + 2:
                continue

            ema_fast = _ema(closes, self.fast)
            ema_slow = _ema(closes, self.slow)
            macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
            signal_line = _ema(macd_line, self.signal)
            # 길이 보정
            L = min(len(macd_line), len(signal_line))
            macd_line, signal_line = macd_line[-L:], signal_line[-L:]
            hist = [m - s for m, s in zip(macd_line, signal_line)]

            sig = self._signals_from_hist(hist)
            if sig and sig[-1] == 1:
                orders.append(OrderRequest.market(sym, "buy", self.qty))
            elif sig and sig[-1] == -1:
                orders.append(OrderRequest.market(sym, "sell", self.qty))
        return orders
