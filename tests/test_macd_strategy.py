from autotrade.models.market import Candle
from autotrade.strategies.macd import MACDStrategy


def test_macd_instantiation_and_generate():
    closes = [
        100,
        101,
        103,
        102,
        101,
        99,
        98,
        100,
        102,
        101,
        103,
        104,
        103,
        105,
        104,
        106,
        107,
        106,
        108,
        110,
    ]
    candles = [Candle(ts=i, o=c, hi=c, lo=c, c=c, v=1.0) for i, c in enumerate(closes)]
    strat = MACDStrategy(
        symbols=["BTC/USDT"], fast=5, slow=10, signal=4, use_crossover=True, cooldown=0
    )
    orders = strat.generate({"BTC/USDT": candles})
    assert isinstance(orders, list)
