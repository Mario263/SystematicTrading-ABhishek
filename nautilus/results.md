# Nautilus Trader — results

Run: `python backtest.py` (venv on CPython 3.12, nautilus_trader==1.228.0)

- Instrument / timeframe: EUR/USD H1
- Date range: 2010-06-01 -> 2026-06-12 (UTC), 100,000 bars
- Position size: 10,000 units (0.1 lot), long-only, flat on exit; init cash 10,000 USD
- OMS: NETTING, MARGIN account, leverage 2 (headroom only)

| Metric | Value |
|---|---|
| Total return | **-15.34%** (realized PnL / init cash) |
| Sharpe ratio | **-0.1413** (per-trade returns, annualised by trades/yr) |
| Max drawdown | **-39.73%** (on realized equity curve) |
| Number of trades | **3895** (result.total_positions) |

Notes:
- MACD/EMA/signal hand-rolled in `MACDStrategy.on_bar` state; no `MovingAverageConvergenceDivergence`.
- **Trade count (3895) is IDENTICAL to vectorbt** -> the hand-rolled MACD + crossover logic and EMA
  seeding match exactly across the two frameworks (resolves finding Q3).
- Return less negative than vectorbt mainly because **this run applies no commission model** while
  vectorbt charges fees on ~7,790 fills (fees are the dominant driver). A secondary factor is fill
  timing/price: vectorbt fills at the bar close, Nautilus fills at the next-bar market price. (Positions
  are flat between trades, so there is no mark-to-market-vs-realized difference.) Direction and trade
  count agree. See root README cross-framework discussion.
- Sharpe computed from per-trade returns, annualised by trades/year over the actual data span (Nautilus
  has no native hourly-return Sharpe matching vectorbt); not numerically comparable to vectorbt's hourly
  Sharpe.
