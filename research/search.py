"""Grid-search the ladder parameters on BOTH windows with the exact simulator."""
import itertools, sys
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import run_strategy, load_bars
import importlib
import main as M

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
B_NEW = load_bars(NEW)
B_OLD = load_bars(OLD)

def grade(params):
    lad = M.Ladder(**params)
    r_new = run_strategy(B_NEW, lad.on_batch)
    lad2 = M.Ladder(**params)
    r_old = run_strategy(B_OLD, lad2.on_batch)
    return r_new, r_old

if __name__ == "__main__":
    # baseline: defaults
    r_new, r_old = grade({})
    print("DEFAULTS new:", r_new)
    print("DEFAULTS old:", r_old)
