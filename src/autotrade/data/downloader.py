# src/autotrade/data/downloader.py
from __future__ import annotations
from pathlib import Path
import csv
from typing import Iterable, Literal
from autotrade.models.market import Candle
from autotrade.exchanges.base import IExchangeClient

HEADER = ["ts", "o", "hi", "lo", "c", "v"]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _dedup(
    existing_ts: set[int], rows: list[tuple[int, float, float, float, float, float]]
):
    return [r for r in rows if r[0] not in existing_ts]


def _read_existing_ts(path: Path) -> set[int]:
    if not path.exists():
        return set()
    out: set[int] = set()
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            # ts가 첫 컬럼
            try:
                out.add(int(row[0]))
            except Exception:
                continue
    return out


def candles_to_rows(
    candles: Iterable[Candle],
) -> list[tuple[int, float, float, float, float, float]]:
    rows = []
    for c in candles:
        rows.append(
            (int(c.ts), float(c.o), float(c.hi), float(c.lo), float(c.c), float(c.v))
        )
    # 시간 오름차순으로 저장
    rows.sort(key=lambda x: x[0])
    return rows


def download_candles(
    exchange: IExchangeClient,
    symbol: str,
    interval: str = "1m",
    limit: int = 200,
    out_path: str = "data/out.csv",
    mode: Literal["w", "a"] = "w",
    dedup: bool = True,
) -> str:
    """
    최신 캔들(최대 200개)을 CSV로 저장하는 MVP 다운로더.
    - mode="w": 파일 새로 생성(헤더 포함)
    - mode="a": 이어쓰기(헤더는 파일 없으면 작성)
    - dedup=True: 같은 ts 중복 제거(append 시 유용)
    """
    candles = list(exchange.get_candles(symbol, interval, limit))
    rows = candles_to_rows(candles)

    path = Path(out_path)
    _ensure_parent(path)

    if mode == "w":
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            for r in rows:
                w.writerow(r)
    else:
        existing = _read_existing_ts(path) if dedup else set()
        rows2 = _dedup(existing, rows) if dedup else rows
        write_header = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(HEADER)
            for r in rows2:
                w.writerow(r)

    return str(path)
