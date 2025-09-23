# src/examples/run_rsi_example.py
# ------------------------------------------------------------
# 간단 실행 예시: ./data/sample_ohlcv.csv 를 읽어 RSI 전략 신호/간단 PnL 확인
# csv 형식 예시: date,open,high,low,close,volume
# ------------------------------------------------------------
import os
import pandas as pd
from autotrade.strategies.rsi import RSIStrategy


def main():
    data_path = os.path.join("data", "sample_ohlcv.csv")
    df = pd.read_csv(data_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    strat = RSIStrategy(
        symbols=["BTC/USDT"],
        period=14,
        buy_th=30.0,
        sell_th=70.0,
        use_crossover=True,
        cooldown=3,
        qty=0.001,
    )
    out = strat.generate_signals(df)
    res = strat.naive_pnl(out, fee=0.001)

    print("=== RSI Example Run ===")
    print(f"Rows: {len(out)}")
    print(f"Signals: {out['signal'].abs().sum()} (buy/sell events)")
    print(f"Total trades: {res['trades']}")
    print(f"Naive PnL: {res['pnl']:.4f}")
    print("\nTail preview:")
    print(out[["date", "close", "rsi", "signal"]].tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
