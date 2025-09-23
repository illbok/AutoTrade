from __future__ import annotations
from typing import Iterable, List
from typing import Dict, Mapping, Union, cast
from dataclasses import dataclass
import time
import uuid
import hashlib
import hmac
import json
import requests
from urllib.parse import urlencode
from autotrade.exchanges.base import IExchangeClient
from autotrade.models.market import Ticker, Candle
from autotrade.models.order import OrderRequest, Order


@dataclass
class UpbitCreds:
    access_key: str
    secret_key: str


class UpbitClient(IExchangeClient):
    name = "upbit"

    def __init__(
        self,
        base_url: str,
        creds: UpbitCreds | None = None,
        live: bool = False,
        timeout: int = 10,
    ):
        self.base = base_url.rstrip("/")
        self.creds = creds
        self.live = live  # 기본 False → 드라이런
        self.timeout = timeout
        self.session = requests.Session()

    # ---- Helpers ----
    def _market(self, symbol: str) -> str:
        # 내부 표기 "KRW-BTC" 또는 "USDT-BTC" 그대로 쓰길 권장.
        # "BTC/USDT" → "USDT-BTC" 변환이 필요하면 별도 매핑 테이블로 처리.
        return symbol

    def _sign_jwt(
        self,
        method: str,
        path: str,
        query: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        assert self.creds is not None, "Private endpoint requires creds"
        payload = {"access_key": self.creds.access_key, "nonce": str(uuid.uuid4())}
        q = ""
        if query:
            q = urlencode(query)
            m = hashlib.sha512()
            m.update(q.encode())
            query_hash = m.hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"
        token = hmac.new(
            self.creds.secret_key.encode(), json.dumps(payload).encode(), hashlib.sha256
        ).hexdigest()
        # 업비트는 JWT 라이브러리 사용 권장이나, 여기선 스텁 형태(서명 과정은 실제 구현 시 점검)
        # 안전하게 하려면 PyJWT 사용: jwt.encode(payload, secret, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    # ---- Public ----
    def get_ticker(self, symbol: str) -> Ticker:
        m = self._market(symbol)
        # 타입을 명시하고, 단 한 번만 params 키워드를 전달
        params_ticker: Dict[str, Union[str, int]] = {"markets": m}
        r = self.session.get(
            f"{self.base}/ticker",
            params=cast(Mapping[str, Union[str, int]], params_ticker),
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()[0]
        return Ticker(symbol=symbol, price=float(data["trade_price"]))

    def get_candles(
        self, symbol: str, interval: str, limit: int = 200
    ) -> Iterable[Candle]:
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
        m = self._market(symbol)
        r = self.session.get(
            f"{self.base}/candles/minutes/{unit}",
            params=cast(
                Mapping[str, Union[str, int]],
                {"market": m, "count": int(min(limit, 200))},
            ),
            timeout=self.timeout,
        )
        r.raise_for_status()
        out: List[Candle] = []
        for row in reversed(r.json()):  # 과거→현재
            # ts: UTC iso → epoch
            ts = int(
                time.mktime(
                    time.strptime(row["candle_date_time_utc"][:19], "%Y-%m-%dT%H:%M:%S")
                )
            )
            out.append(
                Candle(
                    ts=ts,
                    o=float(row["opening_price"]),
                    hi=float(row["high_price"]),
                    lo=float(row["low_price"]),
                    c=float(row["trade_price"]),
                    v=float(row["candle_acc_trade_volume"]),
                )
            )
        return out

    # ---- Private (DRY-RUN by default) ----
    def create_order(self, req: OrderRequest) -> Order:
        if not self.live:
            # 드라이런: 실제 주문 안 내고 체결된 것처럼 반환
            px = self.get_ticker(req.symbol).price
            return Order(
                id=f"DRY-{int(time.time())}",
                symbol=req.symbol,
                side=req.side,
                qty=req.qty,
                price=px,
            )

        assert self.creds is not None, "live mode requires creds"
        # 업비트 실제 주문 POST /orders (JWT 필요) — 실제 구현은 공식 문서대로 PyJWT + query hash 적용 필수
        # 여기서는 안전을 위해 NotImplemented로 막아둡니다.
        raise NotImplementedError("Upbit live orders disabled by default for safety.")
