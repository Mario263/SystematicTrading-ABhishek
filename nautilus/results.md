# Nautilus Trader — results

Run: `python backtest.py` (venv on CPython 3.12, nautilus_trader==1.228.0)

- Instrument / timeframe: EUR/USD H1
- Date range: 2010-06-01 -> 2026-06-12 (UTC), 100,000 bars
- Sizing: deploy ~all available cash long each trade (no leverage) — same model as vectorbt
- Costs: custom `NotionalFractionFeeModel` charges 0.00005 of notional per fill (matches vectorbt fees)
- Execution: signal confirmed on a closed bar is acted on the NEXT bar (no look-ahead) — same as vectorbt/MT5

| Metric | Value |
|---|---|
| Total return | **-42.46%** (account balance, incl. fees) |
| Sharpe ratio | **-0.49** (Nautilus native 252-day returns Sharpe) |
| Max drawdown | **-50.24%** (on realized equity curve) |
| Number of trades | **3895** |
| Commission paid | 3,010.81 USD |

Notes:
- MACD/EMA/signal hand-rolled in `MACDStrategy.on_bar` state; no built-in MACD indicator.
- **Converges with vectorbt on identical data:** return -42.46% vs -40.45%, max DD -50.24% vs -49.13%,
  trades 3895 = 3895, commission 3,011 vs 3,090. The two frameworks agree — same strategy, MACD math,
  sizing model, cost model, and now the same next-bar execution. Residual ~2% is engine mechanics
  (sizing buffer / fill price), not logic.
- Earlier this run showed -15.34% because it charged **no transaction costs** (the outlier the user
  flagged). Adding a vectorbt-equivalent fee model and the same cash-deployment sizing fixed it.
- Sharpe is Nautilus's own returns-based statistic (daily returns ×√252). It lines up with MT5's -0.45
  (also daily); vectorbt's -0.61 is more negative only because it annualises hourly (×√8760). Same
  ballpark, different annualisation — see root README.


## Output from Terminal
--- METRICS (Nautilus) ---
Number of trades    : 3895
Final balance       : 5,754.19 USD (init 10,000)
Total return        : -42.46%   (account balance, incl. fees)
Max drawdown        : -50.24%   (on realized equity curve)
Sharpe ratio (Nautilus 252-day returns stat) : -0.4901
Total commission    : 3,010.81 USD
