import typer
from autotrade.exchanges.upbit import UpbitClient
from autotrade.exchanges.fake import FakeExchange
from autotrade.data.downloader import download_candles
from autotrade.app import run
from autotrade.backtest.engine import backtest
from autotrade.live import run_live
from autotrade.strategies.registry import available
from autotrade.exchanges.base import IExchangeClient


app = typer.Typer(help="AutoTrade CLI")


@app.command()
def trade(config: str = "configs/dev.yaml", loops: int = 1):
    run(config_path=config, loops=loops)


@app.command()
def bt(config: str = "configs/dev.yaml"):
    out_csv = backtest(config)
    print(f"Backtest report written to: {out_csv}")


@app.command()
def live(
    config: str = "configs/dev.yaml", loops: int = 10, sleep_s: int = 5, live: int = 0
):
    # CLI 플래그가 1이면 강제로 실거래 활성화(그 외는 settings.yaml 우선)
    if live == 1:
        # 매우 조심: settings.paper가 true면 무시
        import yaml

        with open(config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        cfg["live"] = True
        with open(config, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True)
    run_live(config, loops=loops, sleep_s=sleep_s)


@app.command()
def strategies():
    for s in available():
        print(s)


@app.command("download")
def download(
    symbol: str = typer.Option(..., help="예: KRW-BTC (Upbit 표기)"),
    interval: str = typer.Option("1m", help="1m/3m/5m/15m/30m/60m/240m"),
    limit: int = typer.Option(200, help="최대 200 (Upbit API 기본 제한)"),
    out: str = typer.Option(..., help="출력 CSV 경로"),
    use_fake: bool = typer.Option(False, help="FakeExchange로 더미 데이터 저장"),
    mode: str = typer.Option("w", help='"w"(새로쓰기) 또는 "a"(이어쓰기)'),
) -> None:  # ← 반환 타입 명시(선택이지만 mypy가 좋아함)
    """
    최신 캔들 CSV 다운로더(MVP). Upbit 공개 API 기준 한 번에 최대 200개.
    """
    ex: IExchangeClient  # ← 공통 인터페이스로 타입 지정

    if use_fake:
        ex = FakeExchange()
    else:
        # 공개 API만 필요하므로 creds 없이 생성
        ex = UpbitClient()

    path = download_candles(
        exchange=ex,
        symbol=symbol,
        interval=interval,
        limit=limit,
        out_path=out,
        mode="a" if mode == "a" else "w",
        dedup=True,
    )
    typer.echo(f"Saved: {path}")


if __name__ == "__main__":
    app()
