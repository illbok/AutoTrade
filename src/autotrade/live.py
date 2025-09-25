# src/autotrade/live.py
from __future__ import annotations
import time
import logging
import traceback
from autotrade.settings import Settings
from autotrade.exchanges.upbit import UpbitClient, UpbitCreds
from autotrade.data.candles import CandleService
from autotrade.strategies.registry import create as create_strategy
from autotrade.execution.executor import Executor
from autotrade.logging_config import setup as setup_logging

log = logging.getLogger("live")


def run_live(config_path: str, loops: int = 10, sleep_s: int = 5):
    setup_logging()

    s = Settings.load(config_path)

    # 안전장치
    if s.live and s.paper:
        log.warning("paper=True 이므로 실거래가 비활성화됩니다 (live 플래그 무시).")
        s.live = False
    if not s.live:
        log.info("DRY-RUN 모드로 실행합니다 (실제 주문이 나가지 않습니다).")

    creds = None
    if s.api.key and s.api.secret:
        creds = UpbitCreds(access_key=s.api.key, secret_key=s.api.secret)
    else:
        if s.live:
            log.error("live=True지만 API 키/시크릿이 없습니다. DRY-RUN으로 강등합니다.")
            s.live = False

    upbit = UpbitClient(
        base_url=s.exchange.base_url,
        creds=creds,
        live=bool(s.live),
        timeout=s.exchange.timeout_s,
    )
    candle = CandleService(upbit)
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )
    execu = Executor(upbit)

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
                executed = execu.submit(orders)
                log.info(f"[{i+1}/{loops}] executed={len(executed)}")
        except Exception as e:
            log.error("loop error: %s", e)
            log.debug(traceback.format_exc())
        time.sleep(sleep_s)
