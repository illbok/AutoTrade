from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, Iterable, List
from autotrade.settings import Settings
from autotrade.exchanges.fake import FakeExchange
from autotrade.data.candles import CandleService
from autotrade.execution.executor import Executor
from autotrade.strategies.registry import create as create_strategy
from autotrade.models.market import Candle
from autotrade.models.order import Order
from autotrade.backtest.metrics import compute_equity_curve


def backtest(config: str, out_dir: str = "reports") -> str:
    s = Settings.load(config)
    ex = FakeExchange()
    candle = CandleService(ex)
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )
    execu = Executor(ex)  # 실거래용 Executor 재사용(신호→주문 생성 흐름 동일)

    # 1) 히스토리 수집
    batches: Dict[str, Iterable[Candle]] = {
        sym: list(candle.fetch(sym, s.data["interval"], s.data["window"]))
        for sym in s.strategy.symbols
    }

    # 2) 전략 시그널 → 주문 생성
    orders = strat.generate(batches)

    # 3) 주문 실행(데모: FakeExchange 즉시 체결)
    fills: List[Order] = execu.submit(orders)

    # 4) 에쿼티 곡선 계산(단일 심볼만 데모)
    symbol = s.strategy.symbols[0]
    curve = compute_equity_curve(
        cash_start=10_000.0,
        fills=fills,
        candles=batches[symbol],
        symbol=symbol,
    )

    # 5) CSV 리포트 저장
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "equity_curve.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "equity", "price"])
        for p in curve:
            w.writerow([p.ts, f"{p.equity:.2f}", f"{p.price:.2f}"])

    return str(csv_path)
