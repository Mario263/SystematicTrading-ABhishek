"""
Nautilus Trader MACD-crossover backtest — EUR/USD H1.

MACD is hand-rolled in the Strategy's on_bar state (EMA/MACD/signal), NOT Nautilus's built-in
MACD indicator. Same EMA seeding as the vectorbt version (seed = SMA of the first N values).

A custom fee model charges the same per-side cost as vectorbt (FEES fraction of notional per fill)
so the Nautilus result is comparable to vectorbt and MT5 (which both bear transaction costs).

Strategy: go LONG on MACD crossing above signal; go FLAT on crossing below.

Run:  python backtest.py   (needs nautilus_trader on Python 3.12 — see README.md)
"""
from decimal import Decimal
from math import isnan, nan
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FeeModel
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
FEES = 0.00005               # ~0.5 pip per side, fraction of notional — matches vectorbt (D7)
VENUE = Venue("SIM")
INSTRUMENT_ID = "EUR/USD.SIM"
BAR_TYPE = "EUR/USD.SIM-1-HOUR-MID-EXTERNAL"


def ema_step(price: float, prev: float, period: int) -> float:
    k = 2.0 / (period + 1.0)
    return price * k + prev * (1.0 - k)


class NotionalFractionFeeModel(FeeModel):
    """Charge `fraction` of notional (fill_px * fill_qty) per fill, like vectorbt's fees."""

    def __init__(self, fraction: float):
        super().__init__()
        self._fraction = max(fraction, 0.0)

    def get_commission(self, order, fill_qty, fill_px, instrument) -> Money:
        notional = float(fill_px) * float(fill_qty)
        return Money(notional * self._fraction, USD)


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
        self._pending = None  # "BUY" / "CLOSE" signal from the previous bar, acted on this bar

    def on_start(self):
        self.subscribe_bars(self._bar_type)

    def on_bar(self, bar: Bar):
        close = float(bar.close)

        # Execute the PREVIOUS bar's signal now — fills at this bar's close, i.e. the bar AFTER the
        # cross was confirmed. This is next-bar execution, matching vectorbt's shifted signals and the
        # MT5 EA (which reads the just-closed bar). No look-ahead.
        if self._pending == "BUY" and self.portfolio.is_flat(self._instrument_id):
            qty = self._affordable_qty(close)
            if int(qty) > 0:
                self.submit_order(self.order_factory.market(
                    instrument_id=self._instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=qty,
                ))
        elif self._pending == "CLOSE" and not self.portfolio.is_flat(self._instrument_id):
            self.close_all_positions(self._instrument_id)
        self._pending = None

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
            # Record the signal; it is acted on at the NEXT bar (see top of on_bar).
            if cross_up:
                self._pending = "BUY"
            elif cross_down:
                self._pending = "CLOSE"

        self._prev_macd = macd_line
        self._prev_signal = self._signal

    def _affordable_qty(self, price: float) -> Quantity:
        # Deploy ~all available cash long (no leverage) — same model as vectorbt's from_signals,
        # so the two converge on identical data. 1% buffer leaves room for the fee.
        account = self.cache.account_for_venue(self._instrument_id.venue)
        free = float(account.balance_free(USD))
        return Quantity.from_int(max(int(free * 0.99 / price), 0))

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


def to_float(x) -> float:
    if isinstance(x, (list, tuple)):
        x = x[0] if x else 0.0
    if isinstance(x, str):
        return float(x.split()[0].replace(",", ""))
    return float(x)


def main() -> None:
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id="TESTER-001"))
    engine.add_venue(
        venue=VENUE, oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        base_currency=USD, starting_balances=[Money(INIT_CASH, USD)],
        default_leverage=Decimal(1),
        fee_model=NotionalFractionFeeModel(FEES),
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

    # ---- metrics ----
    positions = engine.trader.generate_positions_report()
    result = engine.get_result()

    n_trades = int(result.total_positions)
    # total return from the account's final balance (includes commissions/fees)
    account = engine.cache.account_for_venue(VENUE)
    final_balance = float(account.balance_total(USD))
    total_ret = (final_balance - INIT_CASH) / INIT_CASH * 100.0

    # Sharpe: use Nautilus's own returns-based statistic (standard daily returns, annualised by sqrt(252))
    sharpe = next((float(v) for k, v in result.stats_returns.items() if "sharpe" in k.lower()),
                  float("nan"))

    if positions is not None and len(positions) > 0:
        pnl = positions["realized_pnl"].map(to_float).reset_index(drop=True)
        equity = INIT_CASH + pnl.cumsum()
        max_dd = ((equity - equity.cummax()) / equity.cummax()).min() * 100.0
        total_commission = (
            float(positions["commissions"].map(to_float).sum())
            if "commissions" in positions.columns else float("nan")
        )
    else:
        max_dd, total_commission = 0.0, 0.0

    print("--- METRICS (Nautilus) ---")
    print(f"Number of trades    : {n_trades}")
    print(f"Final balance       : {final_balance:,.2f} USD (init {INIT_CASH:,})")
    print(f"Total return        : {total_ret:.2f}%   (account balance, incl. fees)")
    print(f"Max drawdown        : {max_dd:.2f}%   (on realized equity curve)")
    print(f"Sharpe ratio (Nautilus 252-day returns stat) : {sharpe:.4f}")
    print(f"Total commission    : {total_commission:,.2f} USD")
    engine.dispose()


if __name__ == "__main__":
    main()
