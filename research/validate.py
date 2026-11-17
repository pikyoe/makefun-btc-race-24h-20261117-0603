import sys
sys.path.insert(0, ".")
from sim import load_bars
from sim import run_strategy

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
bars = load_bars(NEW)

def make_bah(batch_no):
    state = {"done": False}
    def on_batch(s, batch):
        if batch["seq"] == batch_no and not state["done"]:
            state["done"] = True
            return [{"side": "buy", "symbol": "CBBTC",
                     "notional_quote_units": s.cash, "max_slippage_bps": 300}]
        return []
    return on_batch

print("buy-and-hold (expect PnL +1.067187, trades 1, maxDD 0.021189434):")
print(" ", run_strategy(bars, make_bah(0)))
print("momentum batch24 (expect PnL +2.445627, trades 1, maxDD 0.021189434):")
print(" ", run_strategy(bars, make_bah(24)))
