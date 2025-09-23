# tests/test_rsi_strategy.py
# RSI 컬럼/신호 생성 여부를 프로젝트 표준 타입(Candle) 기반으로 체크
from autotrade.models.market import Candle
from autotrade.strategies.rsi import (
    RSIStrategy,
)  # ← 경로 주의: src/autotrade/strategies/rsi.py

# 클래스명/모듈명은 실제 구현에 맞춰 주세요.


def test_rsi_basic_signals():
    # 간단 캔들 시퀀스 (close만 의미있게 사용)
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

    strat = RSIStrategy(symbols=["BTC/USDT"], period=5, buy_th=30, sell_th=70)
    orders = strat.generate({"BTC/USDT": candles})

    # 최소한 에러 없이 리스트가 나오고, 리스트 타입인지 확인
    assert isinstance(orders, list)
