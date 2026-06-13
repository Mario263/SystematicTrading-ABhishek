# Nautilus Trader — MACD crossover backtest

Same strategy as the vectorbt version, implemented as a `Strategy` subclass. The MACD
(fast EMA 12, slow EMA 26, signal = 9-EMA of MACD) is hand-rolled in `on_bar` state — NOT the
built-in `MovingAverageConvergenceDivergence`. Long on MACD crossing above signal; flat on crossing
below. Acts on completed bars only. EMA seeding (SMA of first N) matches the vectorbt version exactly,
so the two produce the same crossovers (same trade count).

## How to run

Nautilus needs Python 3.11–3.13 (system Python here is 3.14). Build a 3.12 venv with `uv`:

```bash
# from the repo root
uv venv --python 3.12 .venv_naut          # if this errors, use the full python.exe path (see findings.md / D10)
uv pip install --python .venv_naut/Scripts/python.exe nautilus_trader
.venv_naut/Scripts/python.exe nautilus/backtest.py
```

Reads `../data/EURUSD60.csv` (TAB-separated, no header), loads it as H1 bars via `BarDataWrangler`,
runs the low-level `BacktestEngine`, then prints the four metrics from the positions report.

## Output (this run)

| Metric | Value |
|---|---|
| Total return | -15.34% |
| Sharpe ratio | -0.1413 |
| Max drawdown | -39.73% |
| Number of trades | 3895 |

Parameters: EUR/USD H1, 2010-06-01..2026-06-12, init cash 10,000 USD, size 10,000 units (0.1 lot),
long-only/flat, NETTING/MARGIN venue. Metric conventions and why they differ from vectorbt are in
`results.md` and the root README.
