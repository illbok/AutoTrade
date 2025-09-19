from __future__ import annotations
from typing import Iterable, List, Mapping, Union
import time
import requests  # ← 추가: Session 타입, HTTP 호출
from autotrade.exchanges.base import IExchangeClient
from autotrade.models.market import Ticker, Candle
from autotrade.models.order import OrderRequest, Order

BASE = "https://api.upbit.com/v1"


class UpbitPublic(IExchangeClient):
    """공개 API만 사용(시세/캔들). 주문은 추후 JWT 서명 추가."""

    name = "upbit-public"

    def __init__(self, base_url: str = BASE, timeout: int = 10) -> None:
        # ↓ mypy가 속성 존재를 알 수 있도록 타입 명시
        self.base: str = base_url.rstrip("/")
        self.timeout: int = timeout
        self.session: requests.Session = requests.Session()

    def _map_symbol(self, symbol: str) -> str:
        # 내부 표기 "KRW-BTC"/"USDT-BTC" 권장. "BTC/USDT" → "USDT-BTC" 식 변환이 필요하면 여기에 추가.
        return symbol.replace("/", "-")

    def get_ticker(self, symbol: str) -> Ticker:
        m = self._map_symbol(symbol)  # ← _market → _map_symbol 로 수정
        params: Mapping[str, str] = {"markets": m}
        r = self.session.get(f"{self.base}/ticker", params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()[0]
        return Ticker(symbol=symbol, price=float(data["trade_price"]))

    def get_candles(
        self, symbol: str, interval: str, limit: int = 200
    ) -> Iterable[Candle]:
        # 업비트 분봉: /candles/minutes/{unit}?market=KRW-BTC&count=...
        unit_map = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "10m": 10,
            "15m": 15,
            "30m": 30,
            "60m": 60,
            "240m": 240,
        }
        unit = unit_map.get(interval, 1)
        m = self._map_symbol(symbol)

        params: Mapping[str, Union[str, int]] = {"market": m, "count": min(limit, 200)}
        r = self.session.get(
            f"{self.base}/candles/minutes/{unit}",
            params=params,
            timeout=self.timeout,
        )
        r.raise_for_status()

        out: List[Candle] = []
        # 최신→과거 응답이라 과거→현재 순으로 뒤집기
        for row in reversed(r.json()):
            # 예: "2024-06-01T12:34:56+00:00" → 앞 19자리만 사용
            ts_str = row["candle_date_time_utc"][:19]
            ts = int(
                time.mktime(time.strptime(ts_str, "%Y-%m-%dT%H:%M:%S"))
            )  # ← %H 사용
            out.append(
                Candle(
                    ts=ts,
                    o=float(row["opening_price"]),
                    hi=float(row["high_price"]),  # ✅ hi
                    lo=float(row["low_price"]),  # ✅ lo
                    c=float(row["trade_price"]),
                    v=float(row["candle_acc_trade_volume"]),
                )
            )
        return out

    def create_order(self, req: OrderRequest) -> Order:
        # 주문은 JWT 서명 필요 → 추후 구현(실거래 전까지는 PaperBroker/백테스트 사용 권장)
        raise NotImplementedError(
            "Upbit order requires JWT auth; will implement later."
        )
