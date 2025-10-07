from autotrade.exchanges.fake import FakeExchange
from autotrade.data.candles import CandleService
from autotrade.strategies.sma_cross import SmaCross  # 예: 존재 가정
from autotrade.models.market import Candle
from autotrade.execution.executor import Executor


def test_live_loop_smoke(monkeypatch):
    # 1) 가짜 캔들: SMA 교차가 쉽게 나도록 가격 설계
    closes = [100, 101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103, 104, 105]
    candles = [Candle(ts=i, o=c, hi=c, lo=c, c=c, v=1.0) for i, c in enumerate(closes)]

    # 2) CandleService.fetch를 모킹: 항상 위 시퀀스를 반환
    def fake_fetch(self, symbol, interval, window):
        return candles[-window:]

    monkeypatch.setattr(CandleService, "fetch", fake_fetch)

    # 3) 전략: 민감한 SMA로 신호 유도
    strat = SmaCross(symbols=["KRW-BTC"], fast=3, slow=5)

    # 4) Executor + FakeExchange (실주문 X)
    ex = FakeExchange()
    exe = Executor(ex)

    # 5) 한 번의 루프: generate → submit
    orders = strat.generate({"KRW-BTC": candles})
    executed = exe.submit(orders)

    # 최소한 “리스트이며 예외 없이 흘렀다”를 확인
    assert isinstance(orders, list)
    assert isinstance(executed, list)
