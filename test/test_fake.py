from autotrade.exchanges.fake import FakeExchange
from autotrade.models.order import OrderRequest


def test_fake_exchange_order():
    ex = FakeExchange()
    req = OrderRequest.market("BTC/USDT", "buy", 0.001)
    order = ex.create_order(req)
    assert order.symbol == "BTC/USDT"
    assert order.qty == 0.001
    assert order.side == "buy"
