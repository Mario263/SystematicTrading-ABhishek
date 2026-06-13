# vectorbt — MACD crossover backtest

Hand-rolled MACD (fast EMA 12, slow EMA 26, signal = 9-EMA of MACD). Long on MACD crossing above
signal; flat on crossing below. Vectorized backtest via `Portfolio.from_signals`.

## How to run

The system Python is 3.14 (vectorbt needs <=3.12). Use the project's unified 3.12 venv built with `uv`:

```bash
# from the repo root
uv venv --python 3.12 .venv              # if this errors, use the full python.exe path (see findings.md / D10)
uv pip install --python .venv/Scripts/python.exe vectorbt pandas numpy
.venv/Scripts/python.exe vectorbt/backtest.py
```

First run JIT-compiles numba (~30s). Reads `../data/EURUSD60.csv` (TAB-separated, no header).

## Output (this run)

| Metric | Value |
|---|---|
| Total return | -40.45% |
| Sharpe ratio (annualised) | -0.6086 |
| Max drawdown | -49.13% |
| Number of trades | 3895 |

Parameters: EUR/USD H1, 2010-06-01..2026-06-12, init cash 10,000 USD, fees 0.00005/side, long-only/flat.
Sizing: `size=10000` but with no leverage vectorbt caps each order to available cash, so it effectively
deploys ~all cash per trade (the same model the Nautilus run uses). Signals execute on the next bar (no
look-ahead). EMA seeded with the SMA of the first N values.
