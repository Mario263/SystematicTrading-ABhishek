# MetaTrader 5 — Results

**Source:** `ReportTester-5051731132.html` (MetaTrader 5 Strategy Tester Report)

* **Instrument / Timeframe:** EURUSD H1
* **Test Period:** 2010.06.01 – 2026.06.12
* **History Quality:** 99%
* **Initial Deposit:** 10,000 USD
* **Leverage:** 1:100
* **Expert Advisor:** `MACD_Crossover_EA`
* **Parameters:**

  * FastPeriod = 12
  * SlowPeriod = 26
  * SignalPeriod = 9
  * LotSize = 0.10

## Performance Summary

| Metric                   | Value                     |
| ------------------------ | ------------------------- |
| Total Net Profit         | **-3,650.96 USD**         |
| Total Return             | **-36.51%**               |
| Gross Profit             | **57,066.33 USD**         |
| Gross Loss               | **-60,717.29 USD**        |
| Profit Factor            | **0.94**                  |
| Sharpe Ratio             | **-0.45**                 |
| Recovery Factor          | **-0.60**                 |
| Expected Payoff          | **-0.95 USD/trade**       |
| Total Trades             | **3,862**                 |
| Winning Trades           | **1,353 (35.03%)**        |
| Losing Trades            | **2,509 (64.97%)**        |
| Largest Winning Trade    | **343.43 USD**            |
| Largest Losing Trade     | **-178.40 USD**           |
| Average Winning Trade    | **42.18 USD**             |
| Average Losing Trade     | **-24.20 USD**            |
| Maximum Balance Drawdown | **6,038.40 USD (53.22%)** |
| Maximum Equity Drawdown  | **6,130.87 USD (53.63%)** |

## Observations

* The strategy generated **57,066.33 USD** in gross profit but incurred **60,717.29 USD** in gross losses, resulting in a net loss of **3,650.96 USD**.
* Although the average winning trade (**42.18 USD**) was larger than the average losing trade (**24.20 USD**), the low win rate (**35.03%**) prevented the strategy from achieving profitability.
* The strategy experienced a maximum equity drawdown of **53.63%**, indicating substantial risk exposure.
* The negative Sharpe Ratio (**-0.45**) and Recovery Factor (**-0.60**) indicate poor risk-adjusted performance.
* Results align with the findings from VectorBT and Nautilus Trader backtests: the baseline MACD crossover strategy is not profitable on EURUSD over the tested period without additional filters, position management, or risk controls.

## Conclusion

The MACD crossover strategy produced a negative return of **36.51%** over the testing period despite generating more than **57,000 USD** in gross profits. A low win rate combined with prolonged drawdowns resulted in overall negative performance. The backtest demonstrates that a simple MACD crossover approach is insufficient for long-term profitability on EURUSD and would require additional signal filtering, trend confirmation, and risk-management mechanisms before deployment in live trading.
