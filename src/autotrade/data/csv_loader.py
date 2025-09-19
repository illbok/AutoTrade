from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import csv
from autotrade.models.market import Candle


def load_candles_csv(path: str | Path) -> Iterable[Candle]:
    p = Path(path)
    rows: List[Candle] = []
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        # 기대 헤더: ts,o,hi,lo,c,v  (초 단위 ts)
        for row in r:
            rows.append(
                Candle(
                    ts=int(row["ts"]),
                    o=float(row["o"]),
                    hi=float(row["hi"]),
                    lo=float(row["lo"]),
                    c=float(row["c"]),
                    v=float(row["v"]),
                )
            )
    return rows
