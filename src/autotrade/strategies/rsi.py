# src/autotrade/strategies/rsi.py
# ------------------------------------------------------------
# RSI 전략 (AutoTrade 표준 인터페이스 준수)
# - 입력: dict[str, Iterable[Candle]]
# - 출력: list[OrderRequest]
# - SMA Cross와 동일한 인터페이스로 symbols 파라미터를 받습니다.
# ------------------------------------------------------------
from __future__ import annotations
from typing import Iterable, List, Dict
from autotrade.models.market import Candle
from autotrade.models.order import OrderRequest
from autotrade.strategies.registry import register


def _wilder_rsi(closes: List[float], period: int) -> List[float]:
    """
    Wilder's RSI (EMA 형태의 평균 상승/하락)
    반환: RSI 리스트 (초기 period-1 구간은 float('nan'))
    """
    n = len(closes)
    if n == 0:
        return []
    import math

    rsi = [math.nan] * n
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        delta = closes[i] - closes[i - 1]
        gains[i] = max(delta, 0.0)
        losses[i] = max(-delta, 0.0)

    # 초기 평균
    avg_gain = sum(gains[1 : period + 1]) / period if n > period else 0.0
    avg_loss = sum(losses[1 : period + 1]) / period if n > period else 0.0

    # 첫 유효 RSI
    if n > period:
        rs = (avg_gain / avg_loss) if avg_loss != 0 else float("inf")
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    # 이후 EMA 방식의 평균
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i] = 100.0  # 손실 0이면 RSI=100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


@register("rsi")
class RSIStrategy:
    """
    프로젝트 표준:
      - __init__(symbols: list[str], **params)
      - generate(candles: dict[str, Iterable[Candle]]) -> list[OrderRequest]
    파라미터:
      period: int = 14
      buy_th: float = 30.0
      sell_th: float = 70.0
      use_crossover: bool = True    # 임계선 '처음' 교차 시에만 신호
      cooldown: int = 0             # 신호 후 N캔들 동안 추가 신호 억제
      qty: float = 0.001            # 주문 수량(데모용)
    """

    def __init__(
        self,
        symbols: list[str],
        period: int = 14,
        buy_th: float = 30.0,
        sell_th: float = 70.0,
        use_crossover: bool = True,
        cooldown: int = 0,
        qty: float = 0.001,
    ):
        self.name = "rsi"
        self.symbols = symbols
        self.period = period
        self.buy_th = buy_th
        self.sell_th = sell_th
        self.use_crossover = use_crossover
        self.cooldown = cooldown
        self.qty = qty

    def on_start(self) -> None:
        pass

    def _signals_from_rsi(self, rsi: List[float]) -> List[int]:
        """
        rsi 리스트로부터 신호 시퀀스 생성
        signal: 1=매수, -1=매도, 0=대기
        """
        n = len(rsi)
        sig = [0] * n
        if n == 0:
            return sig

        # 교차 방식(권장): 임계선 처음 진입할 때만 신호
        if self.use_crossover:
            below = [False] * n
            above = [False] * n
            for i in range(n):
                v = rsi[i]
                if v != v:  # NaN
                    continue
                below[i] = v <= self.buy_th
                above[i] = v >= self.sell_th

            for i in range(1, n):
                # buy: (어제는 not below) & (오늘 below)
                if below[i] and not below[i - 1]:
                    sig[i] = 1
                # sell: (어제는 not above) & (오늘 above)
                elif above[i] and not above[i - 1]:
                    sig[i] = -1
        else:
            # 임계 구간 체류 중에도 계속 신호(실전은 과매수/과매도 난발 우려)
            for i, v in enumerate(rsi):
                if v != v:
                    continue
                if v <= self.buy_th:
                    sig[i] = 1
                elif v >= self.sell_th:
                    sig[i] = -1

        # 쿨다운 적용: 신호 발생 후 N캔들 동안 추가 신호 0으로
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
            rsi = _wilder_rsi(closes, self.period)
            sig = self._signals_from_rsi(rsi)
            if len(sig) < 2:
                continue

            # 마지막 캔들의 신호만 주문으로 변환(백테스트 루프에서 순차 처리 가정)
            if sig[-1] == 1:
                orders.append(OrderRequest.market(sym, "buy", self.qty))
            elif sig[-1] == -1:
                orders.append(OrderRequest.market(sym, "sell", self.qty))
        return orders
