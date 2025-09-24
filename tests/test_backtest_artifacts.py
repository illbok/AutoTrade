from pathlib import Path
from autotrade.backtest.engine import backtest


def test_backtest_outputs_all(tmp_path: Path):
    out_dir = tmp_path / "reports"
    path = backtest("configs/strategy_macd.yaml", out_dir=str(out_dir))
    assert Path(path).exists()
    # 추가 산출물 확인
    for fn in ("summary.txt", "trades.csv", "equity.png"):
        assert (out_dir / fn).exists()
