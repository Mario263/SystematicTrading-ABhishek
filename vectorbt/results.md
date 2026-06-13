# vectorbt — results

Run: `python backtest.py` (venv on CPython 3.12, vectorbt==1.0.0, numba==0.65.1)

- Instrument / timeframe: EUR/USD H1
- Date range: 2010-06-01 10:00 -> 2026-06-12 20:00 (UTC), 100,000 bars
- Position size: 10,000 units (0.1 lot), long-only, flat on exit; init cash 10,000 USD; fees 0.00005/side
- Execution: signals shifted one bar — orders fill on the bar **after** the cross (no same-bar look-ahead)

| Metric | Value |
|---|---|
| Total return | **-40.45%** |
| Sharpe ratio (annualised, factor 8760) | **-0.6086** |
| Max drawdown | **-49.13%** |
| Number of trades | **3895** |

Notes:
- MACD/EMA/signal all hand-rolled in `backtest.py` (`ema()` + `macd()`); no `vbt.MACD`/`talib`/`pandas_ta`.
- Sharpe annualised with vectorbt's freq="1h" -> ann_factor 8760 (365*24). Not numerically comparable to
  Nautilus (per-trade Sharpe) — see root README.
- Negative return is expected: an unfiltered MACD crossover whipsaws and pays fees on ~7,790 fills.
