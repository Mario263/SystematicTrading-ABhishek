# MetaTrader 5 — results

Source: `ReportTester-5051731132.html` (exported Strategy Tester report) + screenshots in this folder.

- Instrument / timeframe: EUR/USD H1
- Date range: 2010.06.01 - 2026.06.12 (broker feed; 99,506 bars, history quality 99%)
- Account: initial deposit 10,000 USD, leverage 1:100; 0.10 lot, long-only, flat on exit
- EA: `MACD_Crossover_EA.mq5` (hand-rolled EMA/MACD/signal, no iMACD)

| Metric | Value |
|---|---|
| Total return | **-36.51%** (net profit -3,650.96 on 10,000) |
| Sharpe ratio | **-0.45** |
| Max drawdown | **53.22%** (balance drawdown maximal 6,038.40; equity DD 53.63%) |
| Number of trades | **3862** (all long; 1353 won = 35.03%) |

Notes:
- MACD/EMA/signal hand-rolled in the EA via `EmaStep()`; `iClose` is used only to read the closed-bar
  price, not as an indicator. No `iMACD`/`iMA`.
- MT5 ran on the **broker's own EUR/USD H1 feed** (99,506 bars), not `data/EURUSD60.csv` (100,000 bars),
  because the Strategy Tester cannot use an external CSV as the traded symbol. Hence trade count 3862 vs
  3895 in vectorbt/Nautilus, and a different return — expected (different feed, real spread, tick fills).
- Result direction agrees with the other two frameworks: the unfiltered MACD crossover loses money.
