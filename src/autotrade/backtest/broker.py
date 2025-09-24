from __future__ import annotations
from dataclasses import dataclass
from typing import List
from autotrade.models.order import OrderRequest, Order


@dataclass
class Position:
    qty: float = 0.0
    avg: float = 0.0  # 평균단가


@dataclass
class Portfolio:
    cash: float
    pos: Position


class PaperBroker:
    def __init__(self, fee_rate: float = 0.0005, slippage: float = 0.0):
        self.fee_rate = fee_rate
        self.slippage = slippage

    def fill(
        self,
        orders: List[OrderRequest],
        price: float,
        pf: Portfolio,
        ts: int | None = None,
    ) -> List[Order]:
        """시장가 가정. price에 슬리피지 적용, 수수료 현금 차감/가산, 평단 업데이트."""
        out: List[Order] = []
        px = (
            price * (1 + self.slippage)
            if orders and orders[0].side == "buy"
            else price * (1 - self.slippage)
        )

        for i, o in enumerate(orders, start=1):
            notional = px * o.qty
            fee = abs(notional) * self.fee_rate
            if o.side == "buy":
                # 새 평단 = (기존 평가금 + 신규 매수금) / 총수량
                new_qty = pf.pos.qty + o.qty
                if new_qty <= 0:
                    pf.pos.qty = 0.0
                    pf.pos.avg = 0.0
                else:
                    pf.pos.avg = (pf.pos.qty * pf.pos.avg + notional) / new_qty
                    pf.pos.qty = new_qty
                pf.cash -= notional + fee
            else:
                # 매도: 현금 증가, 수수료 차감, 수량 감소
                pf.cash += notional - fee
                pf.pos.qty -= o.qty
                if pf.pos.qty <= 1e-12:
                    pf.pos.qty = 0.0
                    pf.pos.avg = 0.0

            out.append(
                Order(
                    id=f"BK{i}",
                    symbol=o.symbol,
                    side=o.side,
                    qty=o.qty,
                    price=px,
                    ts=ts,
                )
            )
        return out
