# MetaTrader 5 — MACD crossover Expert Advisor

`MACD_Crossover_EA.mq5` implements the same strategy as an MQL5 Expert Advisor. The MACD
(fast EMA 12, slow EMA 26, signal = 9-EMA of MACD) is hand-rolled with `EmaStep()` and per-bar state —
NOT `iMACD`/`iMA`. Long on MACD crossing above signal; flat on crossing below. One decision per
completed bar (new-bar detection). 0.10 lot = 10,000 units, matching the other two frameworks.

> The MT5 Strategy Tester only backtests MQL5 EAs (not Python), so this is the required deliverable
> route (decision D4). Running the tester and exporting the report is the one manual step — it needs a
> Windows MT5 terminal.

## How to run the Strategy Tester and export the report

1. Open MetaTrader 5. **File → Open Data Folder** → copy `MACD_Crossover_EA.mq5` into `MQL5\Experts\`.
2. Open **MetaEditor** (F4), open the file, press **F7** to compile (expect 0 errors).
3. Back in MT5: **View → Strategy Tester** (Ctrl+R).
4. Settings tab:
   - Expert: `MACD_Crossover_EA`
   - Symbol: `EURUSD`
   - Timeframe: `H1`
   - Model: `Every tick` (or "1 minute OHLC" for a faster run)
   - Date: use a custom range and set **From 2010.06.01 To 2026.06.12** (or the longest your broker
     provides — state the actual range used)
   - Deposit: `10000` USD, Leverage to match your broker
5. Click **Start**.
6. When it finishes, open the **Backtest** tab in the results panel, **right-click → Report →
   HTML (Internet Explorer)**, and save it into this `mt5/` folder (e.g. `mt5/StrategyTester_Report.html`).
   Optionally also save a screenshot of the results/graph.
7. Fill in `mt5/results.md` with the four metrics from the report (total net profit / return, Sharpe
   ratio, max drawdown, total trades).

## Notes

- The MT5 run uses your **broker's own EUR/USD H1 history**, not `data/EURUSD60.csv`, so its numbers
  will differ from vectorbt/Nautilus (different feed, spread, fills). That divergence is expected and
  discussed in the root README.
- The MT5 Strategy Tester pre-loads history before the start date, so the EMA warm-up is covered.
