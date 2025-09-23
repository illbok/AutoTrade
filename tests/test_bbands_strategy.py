from autotrade.models.market import Candle
from autotrade.strategies.bbands import BBandsStrategy


def test_bbands_instantiation_and_generate():
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
    strat = BBandsStrategy(
        symbols=["BTC/USDT"],
        window=5,
        k=2.0,
        mode="breakout",
        use_crossover=True,
        cooldown=0,
    )
    orders = strat.generate({"BTC/USDT": candles})
    assert isinstance(orders, list)
