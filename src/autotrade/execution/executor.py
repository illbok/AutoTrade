import logging

from autotrade.models.order import OrderRequest
from autotrade.exchanges.base import IExchangeClient
from autotrade.execution.risk import RiskManager

log = logging.getLogger("executor")


class Executor:
    def __init__(self, exchange: IExchangeClient):
        self.exchange = exchange
        # RiskManager 기본값 설정 (필요시 config에서 받아 적용)
        self.risk = RiskManager(max_orders=5, min_qty=0.0001, cooldown_s=2)

    def update_equity(self, equity: float):
        self.risk.update_equity(equity)

    def submit(self, orders: list[OrderRequest]):
        executed = []
        safe_orders = self.risk.validate(orders)
        for o in safe_orders:
            order = self.exchange.create_order(o)
            executed.append(order)
            log.info(
                f"Executed {order.side} {order.qty} {order.symbol} @ {order.price} (id={order.id})"
            )
        return executed
