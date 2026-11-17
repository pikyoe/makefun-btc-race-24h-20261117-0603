import sys, json
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import run_strategy, load_bars
import main as M

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
B_NEW = load_bars(NEW); B_OLD = load_bars(OLD)
P = json.load(open("final_params.json"))

def ev(p):
    rn = run_strategy(B_NEW, M.Ladder(**p).on_batch)
    ro = run_strategy(B_OLD, M.Ladder(**p).on_batch)
    return rn, ro

rn, ro = ev(P)
print(f"BASE: NEW {rn['pnl_usdc']:+.2f} (trades {rn['trades']}, dd {rn['max_dd']:.4f}) | OLD {ro['pnl_usdc']:+.2f} (trades {ro['trades']}, dd {ro['max_dd']:.4f})")
print()
VARIATIONS = {
    "DIP1_BPS": [80, 120],
    "DIP_STEP_BPS": [32, 48],
    "TP_BPS": [160, 240],
    "TRAIL_ARM_BPS": [96, 144],
    "TRAIL_TIGHT_BPS": [16, 24],
    "TREND240_MIN_BPS": [-180, -120],
    "VOL_HIGH_BPS": [6, 10],
    "DD_GUARD_BPS": [320, 480],
    "MIN_SEP_BARS": [8, 12],
    "LEG_FRACTION_BPS": [8000, 10000],
    "MAX_LEGS": [2, 4],
    "LOOKBACK": [48, 72],
    "TREND_MAX_BPS": [-50, 50],
}
allpos = True
for key, vals in VARIATIONS.items():
    for v in vals:
        q = dict(P); q[key] = v
        rn, ro = ev(q)
        ok = rn["pnl_usdc"] > 0 and ro["pnl_usdc"] > 0
        allpos &= ok
        print(f"  {key}={v}: NEW {rn['pnl_usdc']:+7.2f} (t{rn['trades']}) | OLD {ro['pnl_usdc']:+7.2f} (t{ro['trades']})  {'OK' if ok else 'FAIL'}")
print()
print("ALL VARIATIONS POSITIVE ON BOTH WINDOWS:", allpos)
