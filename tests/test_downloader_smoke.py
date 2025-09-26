from pathlib import Path
from autotrade.exchanges.fake import FakeExchange
from autotrade.data.downloader import download_candles
from autotrade.data.csv_loader import load_candles_csv


def test_download_and_load(tmp_path: Path):
    out = tmp_path / "candles.csv"
    ex = FakeExchange()
    path = download_candles(ex, "KRW-BTC", "1m", 60, str(out), mode="w", dedup=True)
    assert Path(path).exists()
    candles = list(load_candles_csv(str(out)))
    assert len(candles) > 0
    assert hasattr(candles[0], "ts")
