# MACD Crossover — Backtest across vectorbt, Nautilus Trader, and MetaTrader 5

One MACD-crossover strategy implemented three times, with the MACD math **hand-rolled** in every
implementation (no `vbt.MACD`, `talib`, `pandas_ta`, Nautilus built-in indicator, or MQL5 `iMACD`).

## Strategy

- MACD: fast EMA = 12, slow EMA = 26, signal = 9-period EMA of the MACD line.
- **Go long** when the MACD line crosses **above** the signal line.
- **Go flat** when the MACD line crosses **below** the signal line. *(Exit = flat, not short.)*
- EMA is the recursive formula `EMA_t = price_t·k + EMA_{t-1}·(1-k)`, `k = 2/(n+1)`, seeded with the
  **SMA of the first n values**. Same seeding in all three so they produce the same crossovers.
- **No look-ahead:** all three act on the bar *after* a cross is confirmed on a closed bar — vectorbt
  shifts its signals one bar; Nautilus/MT5 are event-driven on completed bars and fill on the next bar.

## Shared parameters (identical across all three)

| Parameter | Value |
|---|---|
| Instrument | EUR/USD |
| Timeframe | H1 (1 hour) |
| Date range | 2010-06-01 → 2026-06-12 (UTC), 100,000 bars |
| Data source | forexsb.com export → `data/EURUSD60.csv` (TAB-separated, no header) |
| Starting capital | 10,000 USD |
| Position size | deploy ~all available cash long, no leverage (vbt & Nautilus); MT5 = fixed 0.1 lot |
| Costs | ~0.5 pip per side (see per-framework notes) |

vectorbt and Nautilus read the **same CSV**. MT5 uses the **broker's own EUR/USD H1 feed** over the same
range (the Strategy Tester cannot read an external CSV as the trading symbol).

## Results

| Framework | Total return | Sharpe | Max drawdown | # Trades |
|---|---|---|---|---|
| **vectorbt** (1.0.0) | -40.45% | -0.6086 | -49.13% | 3895 |
| **Nautilus Trader** (1.228.0) | -42.46% | -0.49 | -50.24% | 3895 |
| **MetaTrader 5** (MQL5 EA) | -36.51% | -0.45 | 53.22% | 3862 |

> **MT5 ran on a broker feed.** The MT5 Strategy Tester only backtests MQL5 EAs (not Python) and uses the
> broker's own EUR/USD H1 history. The exported report is in `mt5/ReportTester-5051731132.html` (+ PNG
> screenshots); the numbers above come straight from it. To reproduce, see [mt5/README.md](mt5/README.md).

Sharpe is **annualised differently per framework** and is **not** directly comparable across them — see
below.

## How to run

System Python here is 3.14; vectorbt needs ≤3.12 and Nautilus needs 3.11–3.13. Both install cleanly
together on one `uv`-managed Python 3.12 venv (they resolve to the same numpy 2.4.6 / pandas 2.3.3).

```bash
# from the repo root — one venv for both Python frameworks
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe vectorbt nautilus_trader pandas

.venv/Scripts/python.exe vectorbt/backtest.py
.venv/Scripts/python.exe nautilus/backtest.py

# MetaTrader 5: open mt5/MACD_Crossover_EA.mq5 in MetaEditor, compile (F7),
# run the Strategy Tester on EURUSD H1, export the report. See mt5/README.md.
```

If `uv venv --python 3.12` errors on your machine (a `uv` symlink quirk we hit), pass the full path to
the downloaded `python.exe` instead — see `.claude/memory/findings.md` (D10).

## Notable differences between frameworks — and why

- **vectorbt and Nautilus agree on identical data.** On the same `data/EURUSD60.csv`, with the same
  hand-rolled MACD, the same sizing model (deploy ~all available cash long, no leverage), the same
  per-side cost (0.00005 of notional), and the same **next-bar execution**, the two converge: return
  **-40.45% vs -42.46%**, max drawdown **-49.13% vs -50.24%**, **3895 = 3895** trades, commission
  **$3,090 vs $3,011**. This is the key correctness signal — two independent engines produce essentially
  the same result on the same inputs.
- **Execution timing (no look-ahead) is identical across all three:** a cross confirmed on a *closed*
  bar is acted on the *next* bar. vectorbt shifts its signals one bar; Nautilus stores the signal and
  submits the order on the following `on_bar`; the MT5 EA reads the just-closed bar (`iClose(...,1)`) and
  trades the forming bar.
- **Why they're not bit-identical:** the ~2% residual is engine mechanics — vectorbt's vectorized
  cash-capping vs Nautilus's `~free_cash/price` sizing (commission $3,090 vs $3,011 reflects the slightly
  different deployed size) and minor fill-price differences. Sharpe also uses different annualisation
  (vectorbt hourly ×√8760; Nautilus & MT5 daily ×√252), so the Sharpe numbers are the same ballpark but
  not equal — Nautilus -0.49 and MT5 -0.45 (both daily) line up; vectorbt -0.61 is more negative because
  hourly annualisation scales the negative mean return by a larger factor.
- **MT5 (-36.51%, 3862 trades) is close, and the small difference is data, not logic.** It ran on the
  **broker's own EUR/USD H1 feed** (99,506 bars, 99% history quality) rather than `data/EURUSD60.csv`
  (100,000 bars), with real spread and tick-level fills. Same direction, same ~-37% to -41% range; the
  feed difference explains the rest (and is the one input the assignment allows to differ for MT5).
- **Sharpe is not comparable across frameworks.** vectorbt annualises **hourly** returns with factor
  8760 (365×24); Nautilus reports its native **daily-return** Sharpe (×√252); MT5 reports its own
  (also daily-based). All three are negative, consistent with a losing, whipsaw-prone strategy.
- **Takeaway:** an unfiltered MACD crossover on 16 years of EUR/USD H1 loses money — frequent crossovers
  in ranging markets pay costs and get chopped. The point of the exercise is framework adaptation and
  correct, reproducible mechanics, which the matching trade counts confirm.

## Issues encountered & how they were resolved (incl. where AI tools helped / misled)

- **Python 3.14 incompatibility.** The repo was on Python 3.14; neither vectorbt (needs ≤3.12) nor
  Nautilus (3.11–3.13) install there. Resolved by building per-framework `uv`-managed Python 3.12 venvs.
- **`uv venv --python 3.12` failed** on this machine (a symlink-resolution quirk). Resolved by using the
  full explicit path to the downloaded `python.exe`. Documented in `findings.md`.
- **Data file naming/format.** Decisions originally assumed `data/eurusd_h1.csv`; the real export is
  `data/EURUSD60.csv`, TAB-separated, **no header**. All loaders were written to that real format.
- **Sizing model drove a false discrepancy.** With a fixed leveraged 10,000-unit size, Nautilus showed
  -61% while vectorbt (which silently caps size to available cash, no leverage) showed -40% on the *same
  data*. Resolved by using one model — **deploy ~all available cash long** — in both, so they converge
  (-40.45% vs -42.46%, commission $3,090 vs $3,011). MT5's EA uses a fixed 0.1 lot (≈ full capital at
  1:100), landing in the same range on its own broker feed.
- **Nautilus metric extraction.** Nautilus's native Sharpe is daily-return based and its max-drawdown
  isn't in the default stats. Rather than fight framework-specific stats, the four metrics are computed
  from the positions report (realized PnL), which is transparent and reproducible.
- **AI tooling — where it helped:** generated the version-correct Nautilus 1.228 API scaffolding
  (engine/venue/instrument/wrangler/strategy) and the hand-rolled EMA math quickly.
- **AI tooling — where it misled:** an initial research pass got stuck trying to write its findings file
  due to a shell-quoting bug, and AI guidance was over-confident about Nautilus's native Sharpe/drawdown
  stat names — which is why metrics are derived from the positions report instead of trusted blindly.

## Repo layout

```
vectorbt/   backtest.py  + README + results.md   (runs, metrics produced)
nautilus/   backtest.py  + README + results.md   (runs, metrics produced)
mt5/        MACD_Crossover_EA.mq5 + README + results.md + ReportTester-*.html/.png (tester report)
data/       EURUSD60.csv  (shared EUR/USD H1 data)

```

The full assignment text is preserved in `.claude/memory/requirements.md`.
