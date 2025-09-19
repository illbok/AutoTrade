from pathlib import Path
from autotrade.backtest.engine import backtest


def test_backtest_outputs_csv(tmp_path: Path, monkeypatch):
    # 임시 디렉터리에 reports 생성되도록
    out_dir = tmp_path / "reports"

    # 간단히 기본 config 경로를 고정(루트 기준). 필요시 Resolve-Path 로직을 공유해도 됨.
    csv_path = backtest("configs/dev.yaml", out_dir=str(out_dir))
    p = Path(csv_path)
    assert p.exists()
    # 헤더 포함 최소 2줄(ts+적어도 한 지점)
    content = p.read_text(encoding="utf-8").strip().splitlines()
    assert content[0].startswith("ts,equity,price")
    assert len(content) >= 2
