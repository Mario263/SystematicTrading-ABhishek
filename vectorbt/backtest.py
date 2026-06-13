"""
vectorbt MACD-crossover backtest — EUR/USD H1.

MACD is hand-rolled (EMA/MACD/signal computed here), NOT a library indicator.
Strategy: go LONG on MACD crossing above signal; go FLAT on crossing below.

Run:  python backtest.py
See README.md in this folder.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

# ---- shared parameters (see .claude/memory/decisions.md) ----
DATA = Path(__file__).resolve().parents[1] / "data" / "EURUSD60.csv"
FAST, SLOW, SIGNAL = 12, 26, 9
INIT_CASH = 10_000.0
SIZE = 10_000.0      # 0.1 standard lot, fixed, long-only (D6)
FEES = 0.00005       # ~0.5 pip per side as fraction of trade value (D7)
FREQ = "1h"


def ema(values: np.ndarray, period: int) -> np.ndarray:
    """EMA via the recursive formula, seeded with the SMA of the first `period` values.
    Values before the seed are NaN. No library indicator used."""
    k = 2.0 / (period + 1.0)
    out = np.full(values.shape, np.nan, dtype=float)
    if len(values) < period:
        return out
    out[period - 1] = values[:period].mean()
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1.0 - k)
    return out


def macd(close: np.ndarray, fast: int, slow: int, signal: int):
    macd_line = ema(close, fast) - ema(close, slow)
    # signal = EMA of the MACD line (not of price); seed EMA over the valid region
    sig = np.full(macd_line.shape, np.nan, dtype=float)
    valid = ~np.isnan(macd_line)
    if valid.sum() >= signal:
        start = np.argmax(valid)  # first non-NaN MACD index
        sig[start:] = ema(macd_line[start:], signal)
    return macd_line, sig


def main() -> None:
    df = pd.read_csv(
        DATA, sep="\t", header=None,
        names=["datetime", "open", "high", "low", "close", "volume"],
        parse_dates=["datetime"],
    ).set_index("datetime")
    close = df["close"]

    macd_line, sig = macd(close.to_numpy(dtype=float), FAST, SLOW, SIGNAL)
    macd_s = pd.Series(macd_line, index=close.index)
    sig_s = pd.Series(sig, index=close.index)

    prev_macd, prev_sig = macd_s.shift(1), sig_s.shift(1)
    cross_up = (prev_macd <= prev_sig) & (macd_s > sig_s)    # cross up -> long
    cross_down = (prev_macd >= prev_sig) & (macd_s < sig_s)  # cross down -> flat
    # Execute on the NEXT bar (shift signals by 1) so the fill never uses the same bar's
    # close that produced the signal — avoids look-ahead and matches Nautilus/MT5, which
    # both act on the bar after the cross is confirmed.
    entries = cross_up.shift(1).fillna(False)
    exits = cross_down.shift(1).fillna(False)

    pf = vbt.Portfolio.from_signals(
        close, entries, exits,
        size=SIZE, direction="longonly",
        init_cash=INIT_CASH, fees=FEES, freq=FREQ,
    )

    print(f"Bars                : {len(close):,}")
    print(f"Date range          : {close.index[0]}  ->  {close.index[-1]}")
    print(f"Entry signals       : {int(entries.sum()):,}")
    print("--- METRICS ---")
    print(f"Total return        : {pf.total_return() * 100:.2f}%")
    print(f"Sharpe ratio (ann.) : {pf.sharpe_ratio():.4f}   (freq=1h, ann_factor=8760)")
    print(f"Max drawdown        : {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of trades    : {pf.trades.count()}")


if __name__ == "__main__":
    main()
