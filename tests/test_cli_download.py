from pathlib import Path
from typer.testing import CliRunner
from autotrade.cli import app

runner = CliRunner()


def test_cli_download_with_fake(tmp_path: Path):
    out = tmp_path / "out.csv"
    # FakeExchange 사용: --use-fake
    result = runner.invoke(
        app,
        [
            "download",
            "--symbol",
            "KRW-BTC",
            "--interval",
            "1m",
            "--limit",
            "30",
            "--out",
            str(out),
            "--use-fake",
            "--mode",
            "w",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    # 헤더 확인
    assert text.splitlines()[0].strip() == "ts,o,hi,lo,c,v"
