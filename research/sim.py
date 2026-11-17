"""Exact offline simulator for agent-fun/bars-replay/v1 (CBBTC, single symbol).

Replicates /tmp/harness/sim/bars/engine.ts fill math with Python ints
(BigInt-identical truncating division on non-negative values):

  buy:  spend = notional * 9996 // 10000
        price = open * 10002 * M.num // (10000 * M.den)   [M from BarsPool.buy(spend)]
        qty   = spend * 10**(qty_scale+price_scale) // (price * 10**quote_scale)
  sell: M from pool.sell(value(qty, open))
        slipped = open * 9998 * M.den // (10000 * M.num)
        price = max(1, slipped)
        gross = value(qty, price); proceeds = gross * 9996 // 10000
  value(q, p) = q * p * 10**quote_scale // 10**(qty_scale + price_scale)

Decision checks (engine.decide): min notional 1 USDC, cash, max_weight 100%,
insufficient_position, below_min_notional on partial sells. Fill-time
max_slippage vs the latest close. Orders on the last batch rejected.
Flatten at the last close vs c_depth. Equity points: start cash, then
equity at every bar close, then cash after flatten; max DD is peak-to-
trough over those points (as a fraction of the peak).
"""
import gzip
import json
import math
import os
from math import gcd

BPS = 10000
FEE_BPS = 4
SLIP_BPS = 2
MIN_NOTIONAL = 1_000_000          # 1 USDC in quote units
QUOTE_SCALE = 6
PRICE_SCALE = 5
QTY_SCALE = 8
START_CASH = 1_000_000_000        # 1000 USDC


def load_bars(kit_dir):
    path = os.path.join(kit_dir, "dataset/bars/CBBTC.ndjson.gz")
    bars = []
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.strip()
            if line:
                b = json.loads(line)
                bars.append({
                    "t": int(b["t"]),
                    "o": int(b["o"]),
                    "h": int(b["h"]),
                    "l": int(b["l"]),
                    "c": int(b["c"]),
                    "o_depth": [int(d) for d in b["o_depth"]],
                    "c_depth": [int(d) for d in b["c_depth"]],
                })
    return bars


def value(q, p):
    return q * p * 10 ** QUOTE_SCALE // 10 ** (QTY_SCALE + PRICE_SCALE)


class BarsPool:
    """Exact port of engine.ts BarsPool (fractions kept reduced)."""

    def __init__(self, yn, yd, kn, kd, unit=10 ** 6):
        g = gcd(yn, yd)
        self.yn, self.yd = yn // g, yd // g
        self.kn, self.kd = kn, kd
        self.unit = unit

    @staticmethod
    def of(depth, quote_scale=QUOTE_SCALE):
        d = [x * 10 ** quote_scale for x in depth]
        prod = 1
        for x in d:
            prod *= x
        total = 0
        for i in range(len(d)):
            other = 1
            for j, x in enumerate(d):
                if j != i:
                    other *= x
            total += other
        g = gcd(prod, total)
        yn, yd = prod // g, total // g
        return BarsPool(yn, yd, yn * yn, yd * yd)

    def buy(self, spend):
        yn2 = self.yn + spend * self.unit * self.yd
        num = self.yn * yn2 * self.kd
        den = self.yd * self.yd * self.kn
        return (num, den, BarsPool(yn2, self.yd, self.kn, self.kd))

    def sell(self, val):
        t = self.kn * self.yd + val * self.unit * self.yn * self.kd
        num = t * self.yd
        den = self.kd * self.yn * self.yn
        return (num, den, BarsPool(self.kn * self.yn, t, self.kn, self.kd))


def buy_fill(notional, open_px, pool):
    spend = notional * (BPS - FEE_BPS) // BPS
    num, den, after = pool.buy(spend)
    price = open_px * (BPS + SLIP_BPS) * num // (BPS * den)
    qty = spend * 10 ** (QTY_SCALE + PRICE_SCALE) // (price * 10 ** QUOTE_SCALE)
    return {"price": price, "spend": spend, "fee": notional - spend,
            "qty": qty, "after": after}


def sell_fill(qty, open_px, pool):
    num, den, after = pool.sell(value(qty, open_px))
    slipped = open_px * (BPS - SLIP_BPS) * den // (BPS * num)
    price = slipped if slipped > 1 else 1
    gross = value(qty, price)
    proceeds = gross * (BPS - FEE_BPS) // BPS
    return {"price": price, "gross": gross, "fee": gross - proceeds,
            "proceeds": proceeds, "after": after}


class Holding:
    __slots__ = ("qty", "cost")

    def __init__(self, qty=0, cost=0):
        self.qty, self.cost = qty, cost


class FakeState:
    """Mirrors the shim's BarsState surface that a strategy uses."""

    def __init__(self, sim):
        self._sim = sim
        self.seq = -1
        self.warming_up = False
        self.hello = {"seed": "1", "caps": {"max_orders_per_bar": 16,
                                             "max_weight_bps": 10000}}

    @property
    def cash(self):
        return self._sim.cash

    @property
    def equity(self):
        return self._sim.equity_now()

    @property
    def positions(self):
        if self._sim.qty > 0:
            return {"CBBTC": Holding(self._sim.qty, self._sim.cost)}
        return {}

    def close(self, symbol):
        return self._sim.latest_close()

    def depth_at(self, symbol):
        c = self._sim.latest_bar()
        return list(c["c_depth"]) if c else None

    def impact_bps(self, symbol, amount):
        depth = self.depth_at(symbol)
        if depth is None:
            return None
        pool = BarsPool.of(depth)
        num, den, _ = pool.buy(amount)
        # (M - 1) * 10000, truncated: M = num/den
        return (num - den) * BPS // den

    def weight_room(self, symbol):
        held = self.positions.get(symbol)
        held_val = value(held.qty, self.close(symbol)) if held else 0
        room = 10000 * self.equity // BPS - held_val
        return room if room > 0 else 0


class Sim:
    """Drive a strategy's on_batch(state, batch) over bars; return metrics."""

    def __init__(self, bars, on_batch):
        self.bars = bars
        self.on_batch = on_batch
        self.cash = START_CASH
        self.qty = 0
        self.cost = 0
        self.trades = 0
        self.fees = 0
        self.rejected = 0
        self.equity_points = [START_CASH]
        self._closes = []
        self._state = FakeState(self)
        self._used_ids = set()
        self._next_id = 1

    def latest_close(self):
        return self._closes[-1] if self._closes else None

    def latest_bar(self):
        return self.bars[len(self._closes) - 1] if self._closes else None

    def equity_now(self):
        e = self.cash
        if self.qty > 0 and self._closes:
            e += value(self.qty, self._closes[-1])
        return e

    def run(self):
        n = len(self.bars)
        pending = []  # (seq, index, order, close) decided, to resolve at next open
        for i, bar in enumerate(self.bars):
            self._closes.append(bar["c"])
            self._state.seq = i
            fills = self._resolve(pending, bar)
            pending = []
            batch = {"seq": i, "t": bar["t"], "fills": fills,
                     "bars": [{"symbol": "CBBTC", "c": str(bar["c"]),
                               "o": str(bar["o"]), "h": str(bar["h"]),
                               "l": str(bar["l"])}]}
            if i == n - 1:
                # last batch: orders rejected (after_end); bot still answers
                orders = self.on_batch(self._state, batch) or []
                self.rejected += len(orders)
                orders = []
            else:
                orders = self.on_batch(self._state, batch) or []
            pending = self._decide(orders, i, bar)
            # equity point at this bar's close (after fills, before next open)
            self.equity_points.append(self.equity_now())
        # flatten at last close vs c_depth
        last = self.bars[-1]
        if self.qty > 0:
            pool = BarsPool.of(last["c_depth"])
            f = sell_fill(self.qty, last["c"], pool)
            self.cash += f["proceeds"]
            self.fees += f["fee"]
            self.qty = 0
            self.cost = 0
        self.equity_points.append(self.cash)
        return self.metrics()

    def _decide(self, orders, seq, bar):
        """Decision checks; returns pending list for next bar's open."""
        pending = []
        buys = 0
        sold = 0
        equity = self.equity_now()
        close = bar["c"]
        for index, o in enumerate(orders):
            side = o.get("side")
            if side == "buy":
                amount = int(o["notional_quote_units"])
                if amount == 0:
                    self.rejected += 1
                    continue
                if amount < MIN_NOTIONAL:
                    self.rejected += 1
                    continue
                if amount > self.cash - buys:
                    self.rejected += 1
                    continue
                held_val = value(self.qty, close)
                if (held_val + amount) * BPS > 10000 * equity:
                    self.rejected += 1
                    continue
                buys += amount
                pending.append((seq, index, o, close))
            elif side == "sell":
                amount = int(o["qty"])
                avail = self.qty - sold
                if amount == 0 or amount > avail:
                    self.rejected += 1
                    continue
                if amount != avail and value(amount, close) < MIN_NOTIONAL:
                    self.rejected += 1
                    continue
                sold += amount
                pending.append((seq, index, o, close))
            else:
                self.rejected += 1
        return pending

    def _resolve(self, pending, bar):
        """Resolve pending orders at this bar's open; return fill dicts."""
        fills = []
        pool = None
        for seq, index, o, close in pending:
            if pool is None:
                pool = BarsPool.of(bar["o_depth"])
            max_slip = int(o.get("max_slippage_bps", 0))
            cid = o.get("client_id") or f"o{self._next_id}"
            self._next_id += 1
            if o["side"] == "buy":
                amount = int(o["notional_quote_units"])
                f = buy_fill(amount, bar["o"], pool)
                if f["price"] * BPS > close * (BPS + max_slip):
                    self.rejected += 1
                    fills.append({"client_id": cid, "symbol": "CBBTC",
                                  "side": "buy", "status": "rejected",
                                  "reason": "max_slippage", "price": "0",
                                  "qty": "0", "notional_quote_units": "0",
                                  "fee_quote_units": "0"})
                    continue
                if f["qty"] == 0:
                    self.rejected += 1
                    fills.append({"client_id": cid, "symbol": "CBBTC",
                                  "side": "buy", "status": "rejected",
                                  "reason": "zero_amount", "price": "0",
                                  "qty": "0", "notional_quote_units": "0",
                                  "fee_quote_units": "0"})
                    continue
                pool = f["after"]
                self.cash -= amount
                self.qty += f["qty"]
                self.cost += amount
                self.trades += 1
                self.fees += f["fee"]
                fills.append({"client_id": cid, "symbol": "CBBTC",
                              "side": "buy", "status": "filled",
                              "price": str(f["price"]), "qty": str(f["qty"]),
                              "notional_quote_units": str(amount),
                              "fee_quote_units": str(f["fee"])})
            else:
                amount = int(o["qty"])
                f = sell_fill(amount, bar["o"], pool)
                if f["price"] * BPS < close * (BPS - max_slip):
                    self.rejected += 1
                    fills.append({"client_id": cid, "symbol": "CBBTC",
                                  "side": "sell", "status": "rejected",
                                  "reason": "max_slippage", "price": "0",
                                  "qty": "0", "notional_quote_units": "0",
                                  "fee_quote_units": "0"})
                    continue
                pool = f["after"]
                self.cash += f["proceeds"]
                self.cost = self.cost * (self.qty - amount) // self.qty if self.qty else 0
                self.qty -= amount
                self.trades += 1
                self.fees += f["fee"]
                fills.append({"client_id": cid, "symbol": "CBBTC",
                              "side": "sell", "status": "filled",
                              "price": str(f["price"]), "qty": str(amount),
                              "notional_quote_units": str(f["proceeds"]),
                              "fee_quote_units": str(f["fee"])})
        return fills

    def metrics(self):
        pnl_usdc = (self.cash - START_CASH) / 1e6
        peak = self.equity_points[0]
        max_dd = 0.0
        for e in self.equity_points:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak else 0.0
            if dd > max_dd:
                max_dd = dd
        return {"pnl_usdc": pnl_usdc, "trades": self.trades,
                "fees_usdc": self.fees / 1e6, "max_dd": max_dd,
                "rejected": self.rejected, "final_cash_usdc": self.cash / 1e6}


def run_strategy(bars, on_batch):
    return Sim(bars, on_batch).run()
