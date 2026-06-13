"""
Nautilus Trader MACD-crossover backtest — EUR/USD H1.

MACD is hand-rolled in the Strategy's on_bar state (EMA/MACD/signal), NOT Nautilus's built-in
MACD indicator. Same EMA seeding as the vectorbt version (seed = SMA of the first N values) so the
two are directly comparable.

Strategy: go LONG on MACD crossing above signal; go FLAT on crossing below.

Run:  python backtest.py   (needs nautilus_trader on Python 3.12 — see README.md)
"""
from decimal import Decimal
from math import isnan, nan, sqrt
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.currencies import EUR, USD
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import (
    AccountType, AggregationSource, BarAggregation, OmsType, OrderSide, PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.trading.strategy import Strategy

# ---- shared parameters (see .claude/memory/decisions.md) ----
DATA = Path(__file__).resolve().parents[1] / "data" / "EURUSD60.csv"
FAST, SLOW, SIGNAL = 12, 26, 9
INIT_CASH = 10_000
TRADE_SIZE = 10_000          # 0.1 lot, fixed, long-only (D6)
VENUE = Venue("SIM")
INSTRUMENT_ID = "EUR/USD.SIM"
BAR_TYPE = "EUR/USD.SIM-1-HOUR-MID-EXTERNAL"


def ema_step(price: float, prev: float, period: int) -> float:
    k = 2.0 / (period + 1.0)
    return price * k + prev * (1.0 - k)


class MACDConfig(StrategyConfig, frozen=True):
    instrument_id: str
    bar_type: str
    trade_size: int = TRADE_SIZE


class MACDStrategy(Strategy):
    def __init__(self, config: MACDConfig):
        super().__init__(config)
        self._instrument_id = InstrumentId.from_str(config.instrument_id)
        self._bar_type = BarType.from_str(config.bar_type)
        self._qty = Quantity.from_int(config.trade_size)
        # hand-rolled MACD state
        self._fast_seed: list[float] = []
        self._slow_seed: list[float] = []
        self._macd_seed: list[float] = []
        self._ema_fast = nan
        self._ema_slow = nan
        self._signal = nan
        self._prev_macd = nan
        self._prev_signal = nan

    def on_start(self):
        self.subscribe_bars(self._bar_type)

    def on_bar(self, bar: Bar):
        close = float(bar.close)

        # fast EMA (seed = SMA of first FAST closes)
        if isnan(self._ema_fast):
            self._fast_seed.append(close)
            if len(self._fast_seed) == FAST:
                self._ema_fast = sum(self._fast_seed) / FAST
        else:
            self._ema_fast = ema_step(close, self._ema_fast, FAST)

        # slow EMA (seed = SMA of first SLOW closes)
        if isnan(self._ema_slow):
            self._slow_seed.append(close)
            if len(self._slow_seed) == SLOW:
                self._ema_slow = sum(self._slow_seed) / SLOW
        else:
            self._ema_slow = ema_step(close, self._ema_slow, SLOW)

        if isnan(self._ema_fast) or isnan(self._ema_slow):
            return  # MACD not defined yet

        macd_line = self._ema_fast - self._ema_slow

        # signal = EMA of MACD line (seed = SMA of first SIGNAL macd values)
        if isnan(self._signal):
            self._macd_seed.append(macd_line)
            if len(self._macd_seed) == SIGNAL:
                self._signal = sum(self._macd_seed) / SIGNAL
            else:
                self._prev_macd = macd_line
                return
        else:
            self._signal = ema_step(macd_line, self._signal, SIGNAL)

        if not isnan(self._prev_macd) and not isnan(self._prev_signal):
            cross_up = self._prev_macd <= self._prev_signal and macd_line > self._signal
            cross_down = self._prev_macd >= self._prev_signal and macd_line < self._signal
            if cross_up and self.portfolio.is_flat(self._instrument_id):
                self.submit_order(self.order_factory.market(
                    instrument_id=self._instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=self._qty,
                ))
            elif cross_down and not self.portfolio.is_flat(self._instrument_id):
                self.close_all_positions(self._instrument_id)

        self._prev_macd = macd_line
        self._prev_signal = self._signal

    def on_stop(self):
        self.close_all_positions(self._instrument_id)


def build_instrument() -> CurrencyPair:
    return CurrencyPair(
        instrument_id=InstrumentId(symbol=Symbol("EUR/USD"), venue=VENUE),
        raw_symbol=Symbol("EUR/USD"),
        base_currency=EUR, quote_currency=USD,
        price_precision=5, size_precision=0,
        price_increment=Price.from_str("0.00001"),
        size_increment=Quantity.from_int(1), lot_size=Quantity.from_int(1),
        ts_event=0, ts_init=0,
    )


def load_bars(instrument, bar_type) -> list[Bar]:
    df = pd.read_csv(
        DATA, sep="\t", header=None,
        names=["timestamp", "open", "high", "low", "close", "volume"],
        parse_dates=["timestamp"], index_col="timestamp",
    )
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df)


def main() -> None:
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id="TESTER-001"))
    engine.add_venue(
        venue=VENUE, oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        base_currency=USD, starting_balances=[Money(INIT_CASH, USD)],
        default_leverage=Decimal(2),
    )
    instrument = build_instrument()
    engine.add_instrument(instrument)

    bar_type = BarType.from_str(BAR_TYPE)
    bars = load_bars(instrument, bar_type)
    engine.add_data(bars)

    engine.add_strategy(MACDStrategy(MACDConfig(
        instrument_id=INSTRUMENT_ID, bar_type=BAR_TYPE, trade_size=TRADE_SIZE,
    )))
    engine.run()

    # ---- metrics from the positions report (closed round-trips) ----
    positions = engine.trader.generate_positions_report()

    def to_float(x) -> float:
        if isinstance(x, str):
            return float(x.split()[0].replace(",", ""))
        return float(x)

    if positions is None or len(positions) == 0:
        n_trades, total_ret, max_dd = 0, 0.0, 0.0
    else:
        pnl = positions["realized_pnl"].map(to_float).reset_index(drop=True)
        n_trades = len(pnl)
        total_pnl = pnl.sum()
        total_ret = total_pnl / INIT_CASH * 100.0
        equity = INIT_CASH + pnl.cumsum()
        peak = equity.cummax()
        max_dd = ((equity - peak) / peak).min() * 100.0
        # Sharpe from per-trade returns, annualised by trades/year (stated; NOT directly
        # comparable to vectorbt's hourly Sharpe — see root README).
        trade_ret = pnl / INIT_CASH
        if trade_ret.std(ddof=1) > 0:
            span_years = (bars[-1].ts_event - bars[0].ts_event) / (365.25 * 24 * 3600 * 1e9)
            tpy = n_trades / span_years  # trades per year over the actual data span
            sharpe = (trade_ret.mean() / trade_ret.std(ddof=1)) * sqrt(tpy)
        else:
            sharpe = float("nan")

    result = engine.get_result()
    print("--- METRICS (Nautilus) ---")
    print(f"Number of trades    : {n_trades}   (result.total_positions={result.total_positions})")
    print(f"Total return        : {total_ret:.2f}%   (realized PnL / init cash)")
    print(f"Max drawdown        : {max_dd:.2f}%   (on realized equity curve)")
    print(f"Sharpe (per-trade, ann. by trades/yr) : {sharpe:.4f}")
    engine.dispose()


if __name__ == "__main__":
    main()
