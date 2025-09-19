import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup(log_dir: str = "logs"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    fh = RotatingFileHandler(
        Path(log_dir) / "trader.log", maxBytes=5_000_000, backupCount=3
    )
    logging.getLogger().addHandler(fh)
