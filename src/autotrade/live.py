# src/autotrade/live.py
from __future__ import annotations
import os  # NEW: .env 값 읽기
import time
import logging
import traceback

from autotrade.settings import Settings
from autotrade.exchanges.upbit import UpbitClient, UpbitCreds
from autotrade.data.candles import CandleService
from autotrade.strategies.registry import create as create_strategy
from autotrade.execution.executor import Executor

from autotrade.logging_config import setup as setup_logging  # NEW: 로깅 구성
from autotrade.notify.hooks import Notifier  # NEW: Slack/Telegram 알림

log = logging.getLogger("live")


def run_live(config_path: str, loops: int = 10, sleep_s: int = 5):
    # --- (1) 로깅 세팅: 콘솔(INFO) + 파일(DEBUG) ---
    setup_logging()  # NEW

    # --- (2) 설정 로드 (.env는 settings.py에서 load_dotenv()로 자동 로드됨) ---
    s = Settings.load(config_path)

    # --- (3) 안전장치: paper/live 가드 ---
    if s.live and s.paper:
        log.warning("paper=True 이므로 실거래가 비활성화됩니다 (live 플래그 무시).")
        s.live = False
    if not s.live:
        log.info("DRY-RUN 모드로 실행합니다 (실제 주문이 나가지 않습니다).")

    # --- (4) API 키/시크릿 확인 ---
    creds = None
    if s.api.key and s.api.secret:
        creds = UpbitCreds(access_key=s.api.key, secret_key=s.api.secret)
    else:
        if s.live:
            log.error("live=True지만 API 키/시크릿이 없습니다. DRY-RUN으로 강등합니다.")
            s.live = False

    # --- (5) 거래소/서비스/전략/실행기 생성 ---
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

    # --- (6) 알림 훅 준비 (환경변수에서 자동 읽기) ---
    notifier = Notifier(  # NEW
        slack_webhook=os.getenv("SLACK_WEBHOOK"),  # NEW
        telegram_bot=os.getenv("TELEGRAM_BOT"),  # NEW
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),  # NEW
    )

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
                # --- (7) 체결 알림 전송 ---
                for o in executed:  # NEW
                    notifier.send(  # NEW
                        f"[{s.env}] {o.side.upper()} {o.qty} {o.symbol} @ {o.price} (id={o.id})"
                    )
                log.info(f"[{i+1}/{loops}] executed={len(executed)}")

        except Exception as e:
            log.error("loop error: %s", e)
            log.debug(traceback.format_exc())
        time.sleep(sleep_s)
