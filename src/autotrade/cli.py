import typer
from autotrade.app import run
from autotrade.backtest.engine import backtest
from autotrade.live import run_live
from autotrade.strategies.registry import available

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


if __name__ == "__main__":
    app()
