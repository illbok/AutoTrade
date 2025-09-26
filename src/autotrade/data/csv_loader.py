# src/autotrade/data/csv_loader.py
from __future__ import annotations
from pathlib import Path
import csv
from typing import Iterable, List
from autotrade.models.market import Candle

REQUIRED = ["ts", "o", "hi", "lo", "c", "v"]


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def load_candles_csv(path: str) -> Iterable[Candle]:
    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")

    with p.open("r", encoding="utf-8-sig") as f:  # BOM 대응
        r = csv.DictReader(f)
        if r.fieldnames is None:
            raise ValueError(f"CSV has no header: {p}")
        missing = [k for k in REQUIRED if k not in r.fieldnames]
        if missing:
            raise ValueError(f"CSV header missing {missing}; expected {REQUIRED}")

        out: List[Candle] = []
        for row in r:
            try:
                out.append(
                    Candle(
                        ts=int(row["ts"]),
                        o=float(row["o"]),
                        hi=float(row["hi"]),
                        lo=float(row["lo"]),
                        c=float(row["c"]),
                        v=float(row["v"]),
                    )
                )
            except Exception:
                # 행 단위 스킵(로그는 최소화)
                continue

    # 시간 오름차순 보장
    out.sort(key=lambda c: c.ts)
    return out
