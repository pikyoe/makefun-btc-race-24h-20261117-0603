import sys
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import run_strategy, load_bars, Sim
import main as M

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
B = load_bars(NEW)
p = {"LOOKBACK": 60, "DIP1_BPS": 80, "DIP_STEP_BPS": 40, "MAX_LEGS": 4, "LEG_FRACTION_BPS": 5000,
     "TP_BPS": 200, "TRAIL_BPS": 150, "TREND_MAX_BPS": 10000, "TREND240_MIN_BPS": -150,
     "TREND240_MAX_BPS": 50, "HOLD_MAX_BARS": 240, "MIN_SEP_BARS": 10, "VOL_HIGH_BPS": 12,
     "MOM_MIN_BPS": 0, "MOM_BARS": 10, "DD_GUARD_BPS": 800}
lad = M.Ladder(**p)
fills_log = []
orig = lad.on_batch
def rec(state, batch):
    for f in batch.get("fills") or []:
        fills_log.append((state.seq, dict(f)))
    return orig(state, batch)
r = run_strategy(B, rec)
print("result:", r)
print("num fills:", len(fills_log))
for seq, f in fills_log:
    print(f"bar {seq}: {f.get('side')} price {f.get('price')} qty {f.get('qty')} notional {f.get('notional_quote_units')} proceeds {f.get('proceeds_quote_units')} fee {f.get('fee_quote_units')}")
