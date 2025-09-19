from autotrade.execution.risk import RiskManager
from autotrade.models.order import OrderRequest


def test_risk_manager_rejects_after_limit(caplog):
    rm = RiskManager(max_orders=2)
    o = OrderRequest.market("BTC/USDT", "buy", 1)

    # 3개의 주문 제출
    orders = rm.validate([o, o, o])

    # 실행된 건 2개만 허용
    assert len(orders) == 2

    # 로그에 "Order rejected" 포함 확인
    assert any("Order rejected" in rec.message for rec in caplog.records)
