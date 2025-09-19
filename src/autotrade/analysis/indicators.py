from typing import Sequence, List


def sma(values: Sequence[float], window: int) -> List[float]:
    out, s = [], 0.0
    for i, v in enumerate(values):
        s += v
        if i >= window:
            s -= values[i - window]
        out.append((s / window) if i + 1 >= window else float("nan"))
    return out
