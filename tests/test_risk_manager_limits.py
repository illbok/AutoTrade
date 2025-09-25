from autotrade.execution.risk import RiskManager
from autotrade.models.order import OrderRequest


def test_risk_max_orders(caplog):
    rm = RiskManager(max_orders=2)
    o = OrderRequest.market("KRW-BTC", "buy", 0.001)
    caplog.set_level("WARNING")
    allowed = rm.validate([o, o, o])
    assert len(allowed) == 2
    assert any("max order limit" in r.message for r in caplog.records)


def test_risk_cooldown(caplog):
    rm = RiskManager(max_orders=5, cooldown_s=10)
    o = OrderRequest.market("KRW-BTC", "buy", 0.001)
    caplog.set_level("WARNING")
    allowed1 = rm.validate([o])
    allowed2 = rm.validate([o])
    assert len(allowed1) == 1
    assert len(allowed2) == 0
    assert any("cooldown" in r.message for r in caplog.records)
