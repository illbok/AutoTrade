from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


DEFAULT_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
CONSOLE_FMT = "%(asctime)s | %(levelname)s | %(message)s"


def setup(
    log_dir: str = "logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    filename: str = "trader.log",
    max_bytes: int = 5_000_000,
    backup_count: int = 3,
) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    # 중복 핸들러 방지
    if getattr(root, "_autotrade_logging_installed", False):
        return

    root.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter(CONSOLE_FMT))
    root.addHandler(ch)

    # 파일 핸들러(회전)
    fh = RotatingFileHandler(
        Path(log_dir) / filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(file_level)
    fh.setFormatter(logging.Formatter(DEFAULT_FMT))
    root.addHandler(fh)

    # 소음 줄이기(서드파티)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # 네임스페이스 기본 레벨
    logging.getLogger("live").setLevel(logging.INFO)
    logging.getLogger("executor").setLevel(logging.INFO)
    logging.getLogger("risk").setLevel(logging.INFO)
    logging.getLogger("strategy").setLevel(logging.INFO)
    logging.getLogger("download").setLevel(logging.INFO)

    root._autotrade_logging_installed = True  # type: ignore[attr-defined]
