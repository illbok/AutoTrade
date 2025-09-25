import logging
import time
from autotrade.models.order import OrderRequest

log = logging.getLogger("risk")


class RiskManager:
    def __init__(
        self,
        max_orders: int = 5,
        min_qty: float | None = None,
        min_notional: float | None = None,
        max_daily_loss: float | None = None,
        max_unrealized_loss: float | None = None,
        cooldown_s: int = 0,
    ):
        self.max_orders = max_orders
        self.min_qty = min_qty
        self.min_notional = min_notional
        self.max_daily_loss = max_daily_loss
        self.max_unrealized_loss = max_unrealized_loss
        self.cooldown_s = cooldown_s

        self.counter = 0
        self.last_order_time: float = 0.0
        self.daily_start_equity: float | None = None
        self.current_equity: float | None = None

    def update_equity(self, equity: float):
        if self.daily_start_equity is None:
            self.daily_start_equity = equity
        self.current_equity = equity

    def validate(self, orders: list[OrderRequest]) -> list[OrderRequest]:
        allowed = []
        now = time.time()

        for o in orders:
            # 1) 최대 주문 수
            if self.counter >= self.max_orders:
                log.warning("Order rejected: max order limit reached")
                continue

            # 2) 쿨다운
            if self.cooldown_s > 0 and now - self.last_order_time < self.cooldown_s:
                log.warning("Order rejected: cooldown active")
                continue

            # 3) 최소 수량
            if self.min_qty is not None and o.qty < self.min_qty:
                log.warning(
                    "Order rejected: qty %.8f < min_qty %.8f", o.qty, self.min_qty
                )
                continue

            # 4) 최소 금액(근사 검사: 필요시 실제 ticker 기반으로 확장)
            if self.min_notional is not None and o.qty < self.min_notional:
                log.warning("Order rejected: notional < min_notional (approx check)")
                continue

            # 5) 일일 손실 한도
            if (
                self.max_daily_loss is not None
                and self.daily_start_equity is not None
                and self.current_equity is not None
            ):
                if self.daily_start_equity > 0:
                    dd = (self.current_equity / self.daily_start_equity) - 1.0
                else:
                    dd = 0.0
                if dd <= -abs(self.max_daily_loss):
                    log.error(
                        "Trading halted: daily loss limit reached (%.2f%%)", dd * 100.0
                    )
                    return []  # 모든 주문 차단

            # 6) 미실현 손익 한도
            if (
                self.max_unrealized_loss is not None
                and self.daily_start_equity is not None
                and self.current_equity is not None
            ):
                threshold = (
                    1.0 - abs(self.max_unrealized_loss)
                ) * self.daily_start_equity
                if self.current_equity <= threshold:
                    log.error("Trading halted: unrealized loss limit reached")
                    return []

            # 통과 → 허용
            allowed.append(o)
            self.counter += 1
            self.last_order_time = now

        return allowed
