# src/autotrade/backtest/engine.py
from __future__ import annotations
from pathlib import Path
import csv
from typing import Dict, Iterable, List
import matplotlib

matplotlib.use("Agg")  # GUI 백엔드 사용 안함
import matplotlib.pyplot as plt  # 차트 저장용
from autotrade.settings import Settings
from autotrade.data.csv_loader import load_candles_csv
from autotrade.data.candles import CandleService
from autotrade.exchanges.fake import FakeExchange
from autotrade.strategies.registry import create as create_strategy
from autotrade.models.market import Candle
from autotrade.models.order import Order, OrderRequest
from autotrade.backtest.broker import PaperBroker, Portfolio, Position
from autotrade.backtest.metrics import (
    max_drawdown,
    trade_pnls,
    sharpe_ratio,
)


def backtest(
    config: str,
    out_dir: str = "reports",
    cash_start: float = 10_000.0,
    fee_rate: float = 0.0005,
    slippage: float = 0.0,
) -> str:
    s = Settings.load(config)

    # 데이터 준비
    batches: Dict[str, Iterable[Candle]] = {}
    if "csv" in s.data:
        for sym in s.strategy.symbols:
            batches[sym] = list(load_candles_csv(s.data["csv"]))
    else:
        ex = FakeExchange()
        candle = CandleService(ex)
        for sym in s.strategy.symbols:
            batches[sym] = list(candle.fetch(sym, s.data["interval"], s.data["window"]))

    # 전략/브로커
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )
    broker = PaperBroker(fee_rate=fee_rate, slippage=slippage)
    pf = Portfolio(cash=cash_start, pos=Position())

    fills: List[Order] = []
    sym = s.strategy.symbols[0]
    candles = list(batches[sym])

    # 롤링 윈도우 실행
    win = s.data["window"]
    for i in range(win, len(candles) + 1):
        window = candles[:i]
        orders: List[OrderRequest] = strat.generate({sym: window})
        if not orders:
            continue
        last = window[-1]
        fills.extend(broker.fill(orders, last.c, pf, ts=last.ts))  # <-- ts 기록

    # 산출물 디렉토리
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1) 에쿼티 곡선 CSV (최종 상태 기준의 마크투마켓)
    eq_path = out / "equity_curve.csv"
    with eq_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "equity", "price", "cash", "qty", "avg"])
        for c in candles:
            equity = pf.cash + pf.pos.qty * c.c
            w.writerow(
                [
                    c.ts,
                    f"{equity:.2f}",
                    f"{c.c:.2f}",
                    f"{pf.cash:.2f}",
                    f"{pf.pos.qty:.8f}",
                    f"{pf.pos.avg:.2f}",
                ]
            )

    # 2) 트레이드 로그 CSV
    trades_path = out / "trades.csv"
    with trades_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "id", "symbol", "side", "qty", "price"])
        for t in fills:
            w.writerow(
                [
                    t.ts or 0,
                    t.id,
                    t.symbol,
                    t.side,
                    f"{t.qty:.8f}",
                    f"{(t.price or 0.0):.2f}",
                ]
            )

    # 3) 요약(summary.txt) + 지표
    last_price = candles[-1].c if candles else 0.0
    final_equity = pf.cash + pf.pos.qty * last_price

    # 지표 계산
    # (a) MDD: 간단히 equity_curve.csv의 equity 열 재구성(최종 포지션 기준)
    eq_vals = [pf.cash + pf.pos.qty * c.c for c in candles]
    mdd, peak_v, trough_v = max_drawdown(eq_vals)

    # (b) 승률/평균PnL: 거래쌍(매수→매도) 기준
    pnls = trade_pnls(fills)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = (wins / len(pnls) * 100.0) if pnls else 0.0
    avg_pnl = (sum(pnls) / len(pnls)) if pnls else 0.0

    # (c) 샤프: 간단히 캔들별 수익률(가격 기준)로 대체(보다 정확히 하려면 포트폴리오 일별 수익률 사용)
    rets = []
    for i in range(1, len(candles)):
        p0 = candles[i - 1].c
        p1 = candles[i].c
        if p0 > 0:
            rets.append(p1 / p0 - 1.0)
    sharpe = sharpe_ratio(rets)

    summary_path = out / "summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(f"final_equity={final_equity:.2f}\n")
        f.write(
            f"cash={pf.cash:.2f}, qty={pf.pos.qty:.8f}, avg={pf.pos.avg:.2f}, last_price={last_price:.2f}\n"
        )
        f.write(f"trades={len(fills)}, closed_trades={len(pnls)}\n")
        f.write(f"win_rate={win_rate:.2f}%\n")
        f.write(f"avg_trade_pnl={avg_pnl:.4f}\n")
        f.write(
            f"max_drawdown={mdd*100:.2f}% (peak={peak_v:.2f} -> trough={trough_v:.2f})\n"
        )
        f.write(f"sharpe={sharpe:.4f}\n")

    # 4) 차트 저장 (equity.png) - 가격 & 에쿼티 같은 축 겹치면 스케일이 달라지므로 보조축 사용
    if candles:
        ts = [c.ts for c in candles]
        px = [c.c for c in candles]
        eq = [pf.cash + pf.pos.qty * c.c for c in candles]

        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(ts, px, label="price")
        ax1.set_xlabel("ts")
        ax1.set_ylabel("price")

        ax2 = ax1.twinx()
        ax2.plot(ts, eq, label="equity")
        ax2.set_ylabel("equity")

        # 간단 범례
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

        png_path = out / "equity.png"
        fig.tight_layout()
        fig.savefig(png_path)
        plt.close(fig)

    return str(eq_path)
