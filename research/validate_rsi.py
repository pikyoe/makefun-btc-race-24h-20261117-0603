"""Reimplement rsi-bollinger's rules (from its stated rules) in the simulator;
expect grade-local's -24.252523, 11 trades, fees 4.752530, maxDD 0.027890262."""
import math, sys
sys.path.insert(0, ".")
from sim import run_strategy, load_bars, value

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
bars = load_bars(NEW)

RSI_BARS, BAND_BARS, BAND_SIGMAS = 14, 20, 2
RSI_ENTRY_BELOW, RSI_EXIT_ABOVE = 30, 70

class S:
    def __init__(self):
        self.typical = []
        self.last = None
        self.first = []
        self.gain = None
        self.loss = None

SER = S()

def push(bar):
    c = float(bar["c"]); h = float(bar["h"]); l = float(bar["l"])
    SER.typical.append((h + l + c) / 3)
    if len(SER.typical) > BAND_BARS:
        SER.typical.pop(0)
    if SER.last is not None:
        change = c - SER.last
        up = change if change > 0 else 0
        down = -change if change < 0 else 0
        if SER.gain is None or SER.loss is None:
            SER.first.append(change)
            if len(SER.first) == RSI_BARS:
                SER.gain = sum(x if x > 0 else 0 for x in SER.first) / RSI_BARS
                SER.loss = sum(-x if x < 0 else 0 for x in SER.first) / RSI_BARS
        else:
            SER.gain = (SER.gain * (RSI_BARS - 1) + up) / RSI_BARS
            SER.loss = (SER.loss * (RSI_BARS - 1) + down) / RSI_BARS
    SER.last = c

def rsi():
    if SER.gain is None or SER.loss is None:
        return None
    moved = SER.gain + SER.loss
    return 50 if moved == 0 else (100 * SER.gain) / moved

def lower_band():
    if len(SER.typical) < BAND_BARS:
        return None
    mean = sum(SER.typical) / BAND_BARS
    var = sum((x - mean) * (x - mean) for x in SER.typical) / BAND_BARS
    return mean - BAND_SIGMAS * math.sqrt(var)

def on_batch(s, batch):
    bar = batch["bars"][0]
    push(bar)
    r = rsi()
    held = s.positions.get("CBBTC")
    if held is not None:
        val = value(held.qty, s.close("CBBTC"))
        if (r is not None and r > RSI_EXIT_ABOVE) or val * 10 >= held.cost * 11 or val * 4 <= held.cost * 3:
            return [{"side": "sell", "symbol": "CBBTC", "qty": held.qty, "max_slippage_bps": 100}]
        return []
    lower = lower_band()
    if r is not None and lower is not None and r < RSI_ENTRY_BELOW and SER.last < lower:
        stake = s.equity
        if stake < 1_000_000:
            return []
        return [{"side": "buy", "symbol": "CBBTC", "notional_quote_units": stake, "max_slippage_bps": 100}]
    return []

print("rsi-bollinger sim (expect PnL -24.252523, trades 11, fees 4.752530, maxDD 0.027890262):")
print(" ", run_strategy(bars, on_batch))
