import logging
from autotrade.models.order import OrderRequest

log = logging.getLogger("risk")

class RiskManager:
    def __init__(self, max_orders: int = 5, min_price: float | None = None):
        self.max_orders = max_orders
        self.min_price = min_price
        self.counter = 0

    def validate(self, orders: list[OrderRequest]):
        allowed = []
        for o in orders:
            if self.counter >= self.max_orders:
                log.warning("Order rejected: max order limit reached")
                continue
            if self.min_price is not None and o.type == "market":
                # 단순히 가격 조건을 확인하려면 Ticker 조회 필요 → 여기서는 스킵
                pass
            allowed.append(o)
            self.counter += 1
        return allowed
