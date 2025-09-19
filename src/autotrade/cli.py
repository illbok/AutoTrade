import typer
from autotrade.app import run
from autotrade.strategies.registry import available

app = typer.Typer(help="AutoTrade CLI")

@app.command()
def trade(config: str = "configs/dev.yaml", loops: int = 1):
    run(config_path=config, loops=loops)

@app.command()
def strategies():
    for s in available():
        print(s)

if __name__ == "__main__":
    app()
