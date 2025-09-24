# src/autotrade/backtest/metrics.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple
from autotrade.models.market import Candle
from autotrade.models.order import Order


@dataclass
class EquityPoint:
    ts: int
    equity: float
    price: float
    cash: float
    qty: float
    avg: float


def max_drawdown(equity: List[float]) -> Tuple[float, float, float]:
    """MDD 계산: (mdd, peak, trough). mdd는 음수(%)로 반환."""
    peak = -1e30
    mdd = 0.0
    peak_v = trough_v = 0.0
    cur_peak_v = 0.0
    for v in equity:
        if v > peak:
            peak = v
            cur_peak_v = v
        dd = (v / cur_peak_v - 1.0) if cur_peak_v else 0.0
        if dd < mdd:
            mdd = dd
            peak_v = cur_peak_v
            trough_v = v
    return (mdd, peak_v, trough_v)


def trade_pnls(fills: List[Order]) -> List[float]:
    """아주 단순: buy 후 sell에서 확정(PnL= (sell_px - buy_px)*qty). 포지션 누적이 아닌 1:1 매칭 가정."""
    pnls: List[float] = []
    stack: List[Order] = []
    for f in fills:
        if f.side.lower() == "buy":
            stack.append(f)
        else:
            if stack:
                b = stack.pop(0)
                if b.price is not None and f.price is not None:
                    pnls.append((f.price - b.price) * min(b.qty, f.qty))
    return pnls


def sharpe_ratio(returns: List[float], eps: float = 1e-12) -> float:
    """간단 샤프(무위험 0, 비연율화). returns는 기간 수익률 시퀀스."""
    if not returns:
        return 0.0
    n = len(returns)
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / max(n - 1, 1)
    std = var**0.5
    return mean / (std + eps)


def equity_curve_from_portfolio(
    candles: Iterable[Candle],
    cash: float,
    qty: float,
    avg: float,
) -> List[EquityPoint]:
    out: List[EquityPoint] = []
    for c in candles:
        eq = cash + qty * c.c
        out.append(
            EquityPoint(ts=c.ts, equity=eq, price=c.c, cash=cash, qty=qty, avg=avg)
        )
    return out
