from __future__ import annotations
import time
import logging
import traceback
from autotrade.settings import Settings
from autotrade.exchanges.upbit import UpbitClient, UpbitCreds
from autotrade.data.candles import (
    CandleService,
)  # 이미 있는 서비스 재사용(필요시 Upbit로 분기)
from autotrade.strategies.registry import create as create_strategy
from autotrade.execution.executor import Executor  # 주문 흐름 재사용(리스크 가드 포함)

log = logging.getLogger("live")


def run_live(config_path: str, loops: int = 10, sleep_s: int = 5):
    s = Settings.load(config_path)

    # 안전장치
    if s.live and s.paper:
        log.warning("Both live and paper true; forcing paper mode.")
        s.live = False
    if not s.live:
        log.info(
            "Running in DRY-RUN mode (no real orders). Use --live 1 to enable live later."
        )

    creds = None
    if s.api.key and s.api.secret:
        creds = UpbitCreds(access_key=s.api.key, secret_key=s.api.secret)

    upbit = UpbitClient(base_url=s.exchange.base_url, creds=creds, live=bool(s.live))
    candle = CandleService(upbit)  # 내부에서 exchange.get_candles 사용
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )
    execu = Executor(upbit)  # 내부 RiskManager 동작

    sym = s.strategy.symbols[0]
    interval = s.data.get("interval", "1m")
    window = int(s.data.get("window", 60))

    for i in range(loops):
        try:
            candles = list(candle.fetch(sym, interval, window))
            orders = strat.generate({sym: candles})
            if not orders:
                log.info(f"[{i+1}/{loops}] no signal")
            else:
                # 주문 가드: 최소 수량 등 체크(필요시 RiskManager 확장)
                executed = execu.submit(orders)
                log.info(f"[{i+1}/{loops}] executed={len(executed)}")
        except Exception as e:
            log.error("loop error: %s", e)
            log.debug(traceback.format_exc())
        time.sleep(sleep_s)
