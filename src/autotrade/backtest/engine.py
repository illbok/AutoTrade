from __future__ import annotations
from pathlib import Path
import csv
from typing import Dict, Iterable, List
from autotrade.settings import Settings
from autotrade.data.csv_loader import load_candles_csv
from autotrade.data.candles import CandleService
from autotrade.exchanges.fake import FakeExchange
from autotrade.strategies.registry import create as create_strategy
from autotrade.models.market import Candle
from autotrade.models.order import Order, OrderRequest
from autotrade.backtest.broker import PaperBroker, Portfolio, Position


def backtest(
    config: str,
    out_dir: str = "reports",
    cash_start: float = 10_000.0,
    fee_rate: float = 0.0005,
    slippage: float = 0.0,
) -> str:
    s = Settings.load(config)

    # 데이터 준비: CSV 경로가 설정에 있으면 CSV, 없으면 FakeExchange에서 즉시 로드
    # 설정 예: data: { interval: "1m", window: 300, csv: "data/BTCUSDT_1m.csv" }
    batches: Dict[str, Iterable[Candle]] = {}
    if "csv" in s.data:
        for sym in s.strategy.symbols:
            batches[sym] = list(load_candles_csv(s.data["csv"]))
    else:
        ex = FakeExchange()
        candle = CandleService(ex)
        for sym in s.strategy.symbols:
            batches[sym] = list(candle.fetch(sym, s.data["interval"], s.data["window"]))

    # 전략
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )

    # 브로커/포트폴리오
    broker = PaperBroker(fee_rate=fee_rate, slippage=slippage)
    pf = Portfolio(cash=cash_start, pos=Position())

    fills: List[Order] = []
    # 단일 심볼 기준(확장시 루프 분배)
    sym = s.strategy.symbols[0]
    candles = list(batches[sym])

    # 롤링 윈도우로 전략 신호 생성 → 브로커 체결
    win = s.data["window"]
    for i in range(win, len(candles) + 1):
        window = candles[:i]
        orders: List[OrderRequest] = strat.generate({sym: window})
        if not orders:
            continue
        last_price = window[-1].c
        fills.extend(broker.fill(orders, last_price, pf))

    # 에쿼티 곡선 저장
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    eq_path = out / "equity_curve.csv"
    with eq_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "equity", "price", "cash", "qty", "avg"])
        for c in candles:
            equity = pf.cash + pf.pos.qty * c.c  # 단순 마크투마켓 (마지막 포지션 기준)
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

    # 요약 저장
    summary_path = out / "summary.txt"
    last_price = candles[-1].c
    final_equity = pf.cash + pf.pos.qty * last_price
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(f"final_equity={final_equity:.2f}\n")
        f.write(
            f"cash={pf.cash:.2f}, qty={pf.pos.qty:.8f}, avg={pf.pos.avg:.2f}, last_price={last_price:.2f}\n"
        )

    return str(eq_path)
