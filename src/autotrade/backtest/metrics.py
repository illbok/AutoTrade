from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict
from autotrade.models.market import Candle
from autotrade.models.order import Order


@dataclass
class EquityPoint:
    ts: int
    equity: float
    price: float


def compute_equity_curve(
    cash_start: float,
    fills: List[Order],
    candles: Iterable[Candle],
    symbol: str,
) -> List[EquityPoint]:
    """단일 심볼, 단순 현금+보유수량 기반 에쿼티 곡선."""
    fills_by_ts: Dict[int, float] = {}  # ts -> net_qty change @ fill price
    # 간단화를 위해 주문 체결 시점 가격을 보유수량 가중 평균에 반영하지 않고
    # 보유수량만 변경(마켓가 체결로 가정)
    # 필요 시, fills에 체결가를 넣어 평균단가 추적 로직을 추가하세요.
    qty = 0.0
    equity = cash_start
    curve: List[EquityPoint] = []

    # 체결 수량 집계
    # Order에 체결가가 있다면 avg price를 추적하도록 확장 가능
    for f in fills:
        # 가정: buy는 +qty, sell은 -qty
        dq = f.qty if f.side.lower() == "buy" else -f.qty
        fills_by_ts.setdefault(
            0, 0.0
        )  # 단순화(체결 시점 미사용). 필요 시 Order에 ts 추가.
        fills_by_ts[0] += dq

    # 캔들 순회하며 에쿼티 계산 (종가 기준)
    for c in candles:
        if 0 in fills_by_ts:
            qty += fills_by_ts[0]
            # 체결대금은 반영하지 않음(데모). 실제는 cash에서 체결가*수량을 차감/증가하세요.
            fills_by_ts.pop(0)

        equity = equity  # 현금 변화 없음(데모). 실제는 cash 업데이트 필요.
        # 보유수량 평가손익
        equity_marked = equity + qty * c.c
        curve.append(EquityPoint(ts=c.ts, equity=equity_marked, price=c.c))

    return curve
