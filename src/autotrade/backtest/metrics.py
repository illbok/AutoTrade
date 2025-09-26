# src/autotrade/backtest/metrics.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple
from autotrade.models.market import Candle
from autotrade.models.order import Order
import statistics
import math


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


def cagr(equity_curve: List[float], years: float) -> float:
    """
    안전한 CAGR:
    - 기간이 너무 짧으면(연환산이 의미 없으면) 0.0 반환
    - 시작/끝 에쿼티가 양수일 때만 계산
    - 로그 방식(exp(log(ratio)/years)-1)으로 오버플로 완화
    """
    MIN_YEARS = 1.0 / 365.0  # 최소 1일 이상 데이터에서만 연환산
    if (not equity_curve) or years < MIN_YEARS:
        return 0.0
    initial = float(equity_curve[0])
    final = float(equity_curve[-1])
    if initial <= 0.0 or final <= 0.0:
        return 0.0
    ratio = final / initial
    try:
        val = math.exp(math.log(ratio) / years) - 1.0
        # 수치 폭주 방지용 클램핑 (과도한 이상치 차단)
        if not math.isfinite(val):
            return 0.0
        # 선택: 현실적인 범위로 잘라내기
        return max(-0.9999, min(val, 100.0))
    except (ValueError, OverflowError):
        return 0.0


def calmar(cagr_val: float, mdd: float) -> float:
    """Calmar ratio: CAGR / |MDD|  (MDD는 음수 퍼센트가 아니라 -0.12 같은 비율로 들어온다고 가정)"""
    if mdd == 0:
        return 0.0
    return cagr_val / abs(mdd)


def sortino(returns: List[float]) -> float:
    """Sortino ratio: mean(returns) / std(returns where r<0)"""
    if not returns:
        return 0.0
    mean = statistics.fmean(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return float("inf")
    # 모집단 표준편차 사용 (샤프는 위에서 표본분산으로 계산)
    downside_std = statistics.pstdev(downside)
    if downside_std <= 1e-12:
        return float("inf")
    return mean / downside_std


def drawdown_periods(equity_curve: List[float]) -> Tuple[int, int]:
    """
    (MDD 기간, 리커버리 기간)
    - MDD 기간: 최고점->최저점까지의 길이
    - 리커버리 기간: 최저점 이후 이전 최고점(peak) 회복까지의 길이 (미회복 시 0)
    """
    if not equity_curve:
        return (0, 0)
    peak = equity_curve[0]
    peak_idx = 0
    mdd = 0.0
    mdd_start = mdd_end = 0

    for i, v in enumerate(equity_curve):
        if v > peak:
            peak = v
            peak_idx = i
        dd = v / peak - 1.0
        if dd < mdd:
            mdd = dd
            mdd_start, mdd_end = peak_idx, i

    mdd_period = max(mdd_end - mdd_start, 0)

    # 리커버리: mdd_end 이후에 peak 이상을 다시 찍는 첫 지점
    recovery = 0
    if mdd_end < len(equity_curve) - 1:
        # 당시 peak 값 재계산
        ref_peak = equity_curve[mdd_start] if mdd_start < len(equity_curve) else peak
        for j in range(mdd_end + 1, len(equity_curve)):
            if equity_curve[j] >= ref_peak:
                recovery = j - mdd_end
                break

    return (mdd_period, recovery)
