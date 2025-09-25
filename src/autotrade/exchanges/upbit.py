# src/autotrade/exchanges/upbit.py
from __future__ import annotations
from typing import Iterable, List, Dict, Any, Optional
from dataclasses import dataclass
import time
import hashlib
import uuid
import logging
from urllib.parse import urlencode
import requests
import jwt  # PyJWT

from autotrade.exchanges.base import IExchangeClient
from autotrade.models.market import Ticker, Candle
from autotrade.models.order import OrderRequest, Order

log = logging.getLogger("upbit")

BASE = "https://api.upbit.com/v1"


@dataclass
class UpbitCreds:
    access_key: str
    secret_key: str


class UpbitClient(IExchangeClient):
    """Upbit Public + (안전 장치 포함) Private 주문"""

    name = "upbit"

    def __init__(
        self,
        base_url: str = BASE,
        creds: UpbitCreds | None = None,
        live: bool = False,
        timeout: int = 10,
        session: Optional[requests.Session] = None,
    ):
        self.base = base_url.rstrip("/")
        self.creds = creds
        self.live = live
        self.timeout = timeout
        self.s = session or requests.Session()

    # --- Helper: 시장 심볼 ---
    def _market(self, symbol: str) -> str:
        """
        내부 표기 'KRW-BTC' 그대로 쓰길 권장.
        만약 'BTC/USDT'와 같은 슬래시 표기를 쓰고 있다면, 프로젝트 레벨에서 변환을 거쳐 들어오게 하세요.
        """
        return symbol

    # --- Helper: 쿼리해시 + JWT ---
    def _jwt_headers(self, query: Dict[str, Any]) -> Dict[str, str]:
        assert self.creds is not None, "Private endpoint requires credentials"

        # 업비트는 query_string(SHA512) 해시를 JWT payload에 포함
        query_string = urlencode(query) if query else ""
        query_hash = (
            hashlib.sha512(query_string.encode()).hexdigest() if query_string else None
        )

        payload = {
            "access_key": self.creds.access_key,
            "nonce": str(uuid.uuid4()),
        }
        if query_hash:
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        # HS256 서명
        token = jwt.encode(payload, self.creds.secret_key, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    # --- Public API ---
    def get_ticker(self, symbol: str) -> Ticker:
        m = self._market(symbol)
        params = {"markets": m}
        r = self.s.get(f"{self.base}/ticker", params=params, timeout=self.timeout)
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
        params = {"market": m, "count": str(min(limit, 200))}
        r = self.s.get(
            f"{self.base}/candles/minutes/{unit}",
            params=params,
            timeout=self.timeout,
        )
        r.raise_for_status()
        out: List[Candle] = []
        for row in reversed(r.json()):  # 과거→현재
            # candle_date_time_utc: "YYYY-MM-DDTHH:MM:SS"
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

    # --- Private: 주문 생성 ---
    def _post(self, path: str, query: Dict[str, Any]) -> Dict[str, Any]:
        # 429/5xx 간단 백오프
        backoff = 0.5
        for attempt in range(5):
            headers = self._jwt_headers(query)
            try:
                r = self.s.post(
                    f"{self.base}{path}",
                    params=query,
                    headers=headers,
                    timeout=self.timeout,
                )
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    raise requests.HTTPError(
                        f"retryable status {r.status_code}", response=r
                    )
                r.raise_for_status()
                return r.json()
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                log.warning(
                    f"POST {path} failed (status={status}), retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 8.0)
        raise RuntimeError(f"POST {path} failed after retries")

    def create_order(self, req: OrderRequest) -> Order:
        """
        안전 규칙:
          - (기본) DRY-RUN: self.live=False 이면 실제 주문 X
          - 실주문 조건: self.live=True AND creds 존재
          - 시장가:
             * 매수: ord_type=price, price=투입 금액(KRW 등), volume=""  (전략에서 qty 대신 금액을 전달해야 현실적)
             * 매도: ord_type=market, volume=수량, price=""
        여기서는 데모로 다음을 가정합니다:
          - 'buy' 요청의 qty는 "수량"이 아니라 "투입 금액"으로 해석 (예: 10000 → 1만원 시장가 매수)
          - 'sell' 요청의 qty는 "매도 수량"
        프로젝트 정책에 맞춰 해석/파라미터화를 조정하세요.
        """
        symbol = req.symbol
        side = req.side.lower()
        m = self._market(symbol)

        # DRY-RUN (기본)
        if not self.live or self.creds is None:
            px = self.get_ticker(symbol).price
            # DRY-RUN 규칙:
            # - buy: qty를 '금액'으로 받았더라도 체결가/수량은 계산하지 않고 Order만 기록
            # - sell: qty는 전달된 수량
            return Order(
                id=f"DRY-{int(time.time())}",
                symbol=symbol,
                side=side,
                qty=req.qty,
                price=px,
            )

        # --- 실주문 ---
        # 파라미터 직렬화
        if side == "buy":
            # 시장가 매수: 금액 기반
            query = {
                "market": m,
                "side": "bid",  # bid=매수
                "ord_type": "price",  # 금액 지정 시장가
                "price": f"{req.qty:.8f}",  # qty를 '금액'으로 해석
            }
        elif side == "sell":
            # 시장가 매도: 수량 기반
            query = {
                "market": m,
                "side": "ask",  # ask=매도
                "ord_type": "market",  # 수량 지정 시장가
                "volume": f"{req.qty:.8f}",
            }
        else:
            raise ValueError(f"Unsupported side: {req.side}")

        data = self._post("/orders", query)
        # 응답 예시에서 체결가를 바로 제공하지 않을 수 있으므로, 이력 조회가 필요할 수 있습니다.
        # 여기서는 단순히 요청 직후의 ticker로 ‘근사’ 체결가를 기록합니다.
        px = self.get_ticker(symbol).price
        return Order(
            id=str(data.get("uuid", f"UP-{int(time.time())}")),
            symbol=symbol,
            side=side,
            qty=req.qty,
            price=px,
        )
