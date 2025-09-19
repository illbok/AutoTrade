import logging
from autotrade.settings import Settings
from autotrade.logging_config import setup as setup_logging
from autotrade.exchanges.fake import FakeExchange
from autotrade.data.candles import CandleService
from autotrade.execution.executor import Executor
from autotrade.strategies.registry import create as create_strategy

log = logging.getLogger("app")


def run(config_path: str, loops: int = 1, sleep_s: int = 1):
    setup_logging()
    s = Settings.load(config_path)
    ex = FakeExchange()
    candle = CandleService(ex)
    strat = create_strategy(
        s.strategy.name, **s.strategy.params, symbols=s.strategy.symbols
    )
    execu = Executor(ex)

    strat.on_start()
    for i in range(loops):
        batches = {
            sym: candle.fetch(sym, s.data["interval"], s.data["window"])
            for sym in s.strategy.symbols
        }
        orders = strat.generate(batches)
        execu.submit(orders)
        log.info(f"loop={i+1}/{loops} orders={len(orders)}")
