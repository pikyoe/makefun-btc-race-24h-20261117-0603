import random, sys, json
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import run_strategy, load_bars
import main as M

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
B_NEW = load_bars(NEW); B_OLD = load_bars(OLD)

SPACE = {
    "DIP1_BPS": [80, 100, 120, 150],
    "DIP_STEP_BPS": [30, 40, 60],
    "MAX_LEGS": [2, 3, 4],
    "LEG_FRACTION_BPS": [2000, 2500, 3333],
    "TP_BPS": [80, 100, 120, 150, 200],
    "TRAIL_BPS": [50, 70, 100, 150, 250, 10000],
    "TREND_MAX_BPS": [-50, 0, 50, 10000],
    "TREND240_MIN_BPS": [-10000, -300, -150],
    "TREND240_MAX_BPS": [-50, 50, 10000],
    "HOLD_MAX_BARS": [120, 240, 10000],
    "MIN_SEP_BARS": [30, 60],
    "VOL_HIGH_BPS": [8, 12, 10000],
    "MOM_MIN_BPS": [0, 20],
    "DD_GUARD_BPS": [400, 800, 10000],
}

def score(rn, ro):
    if ro["pnl_usdc"] <= 0:
        return -100 + ro["pnl_usdc"]
    if rn["max_dd"] > 0.05:
        return rn["pnl_usdc"] - 50
    return rn["pnl_usdc"] + min(ro["pnl_usdc"], 5.0)

rng = random.Random(20261117)
results = []
N = 4000
for k in range(N):
    p = {key: rng.choice(vals) for key, vals in SPACE.items()}
    rn = run_strategy(B_NEW, M.Ladder(**p).on_batch)
    ro = run_strategy(B_OLD, M.Ladder(**p).on_batch)
    s = score(rn, ro)
    results.append((s, rn["pnl_usdc"], ro["pnl_usdc"], rn["trades"], ro["trades"], rn["max_dd"], ro["max_dd"], p))
    if (k+1) % 1000 == 0:
        print(f"...{k+1}/{N}", flush=True)

results.sort(key=lambda x: -x[0])
print("\nTOP 15 by score (score, new PnL, old PnL, new trades, old trades, new DD, old DD):")
for r in results[:15]:
    print(f"score {r[0]:7.2f} new {r[1]:+7.2f} old {r[2]:+7.2f} trades {r[3]}/{r[4]} dd {r[5]:.4f}/{r[6]:.4f}")
    print("   ", json.dumps(r[7]))
with open("random_search_top.json", "w") as f:
    json.dump([{"score": r[0], "new": r[1], "old": r[2], "new_trades": r[3], "old_trades": r[4],
                "new_dd": r[5], "old_dd": r[6], "params": r[7]} for r in results[:50]], f, indent=1)
# best NEW regardless of old (for reference)
by_new = sorted(results, key=lambda x: -x[1])
print("\nTOP 5 by NEW PnL alone:")
for r in by_new[:5]:
    print(f"new {r[1]:+7.2f} old {r[2]:+7.2f} trades {r[3]}/{r[4]} dd {r[5]:.4f}/{r[6]:.4f} {json.dumps(r[7])}")
