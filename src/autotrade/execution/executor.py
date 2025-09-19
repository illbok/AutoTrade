import logging

from autotrade.models.order import OrderRequest, Order
from autotrade.exchanges.base import IExchangeClient
from autotrade.execution.risk import RiskManager   # ← Milestone2에서 추가한 리스크 매니저

log = logging.getLogger("executor")


class Executor:
    def __init__(self, exchange: IExchangeClient):
        self.exchange = exchange
        self.risk = RiskManager(max_orders=5)

    def submit(self, orders: list[OrderRequest]) -> list[Order]:
        executed: list[Order] = []

        # 리스크 매니저로 필터링
        safe_orders = self.risk.validate(orders)

        for o in safe_orders:
            order = self.exchange.create_order(o)   # IExchangeClient 프로토콜을 따르는 객체
            executed.append(order)
            log.info(
                f"Executed {order.side} {order.qty} {order.symbol} @ {order.price} (id={order.id})"
            )

        return executed
