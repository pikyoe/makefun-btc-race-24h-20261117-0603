import sys, json
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import run_strategy, load_bars
import main as M

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
B_NEW = load_bars(NEW); B_OLD = load_bars(OLD)

C0 = {"LOOKBACK": 60, "DIP1_BPS": 100, "DIP_STEP_BPS": 40, "MAX_LEGS": 3, "LEG_FRACTION_BPS": 10000,
      "TP_BPS": 300, "TRAIL_BPS": 10000, "TRAIL_ARM_BPS": 120, "TRAIL_TIGHT_BPS": 50,
      "TREND_MAX_BPS": 0, "TREND240_MIN_BPS": -150, "TREND240_MAX_BPS": 10000,
      "HOLD_MAX_BARS": 10000, "MIN_SEP_BARS": 10, "VOL_HIGH_BPS": 8, "MOM_MIN_BPS": 0,
      "MOM_BARS": 5, "REC_BPS": 0, "REC_BARS": 20, "DD_GUARD_BPS": 400}

NEIGHBORS = {
    "LOOKBACK": [20, 30, 45, 60, 90],
    "DIP1_BPS": [70, 80, 90, 100, 110, 120, 130],
    "DIP_STEP_BPS": [20, 30, 40, 50, 60, 80],
    "MAX_LEGS": [1, 2, 3, 4],
    "LEG_FRACTION_BPS": [5000, 7500, 10000],
    "TP_BPS": [150, 200, 250, 300, 400, 10000],
    "TRAIL_BPS": [100, 150, 200, 250, 10000],
    "TRAIL_ARM_BPS": [60, 80, 100, 120, 150, 200, 10000],
    "TRAIL_TIGHT_BPS": [20, 30, 50, 70, 100, 150],
    "TREND_MAX_BPS": [-50, 0, 25, 50, 10000],
    "TREND240_MIN_BPS": [-300, -200, -150, -100, -10000],
    "TREND240_MAX_BPS": [-50, 0, 50, 100, 10000],
    "HOLD_MAX_BARS": [120, 180, 240, 360, 10000],
    "MIN_SEP_BARS": [5, 10, 20, 30, 60],
    "VOL_HIGH_BPS": [6, 8, 10, 12, 10000],
    "MOM_MIN_BPS": [0, 10, 20, 40],
    "MOM_BARS": [5, 10],
    "REC_BPS": [0, 10, 20, 30],
    "REC_BARS": [10, 20],
    "DD_GUARD_BPS": [200, 300, 400, 600, 800, 10000],
}

def ev(p):
    rn = run_strategy(B_NEW, M.Ladder(**p).on_batch)
    ro = run_strategy(B_OLD, M.Ladder(**p).on_batch)
    return rn, ro

def score(rn, ro):
    # maximize NEW subject to OLD >= 2 and NEW dd <= 5%
    if ro["pnl_usdc"] < 2.0 or rn["max_dd"] > 0.05:
        return -100 + min(ro["pnl_usdc"], 0) + rn["pnl_usdc"] * 0.01
    return rn["pnl_usdc"] + min(ro["pnl_usdc"], 5.0)

best = dict(C0)
brn, bro = ev(best)
bs = score(brn, bro)
print(f"start: new {brn['pnl_usdc']:+.2f} old {bro['pnl_usdc']:+.2f} trades {brn['trades']}/{bro['trades']} dd {brn['max_dd']:.4f}/{bro['max_dd']:.4f} score {bs:.2f}")
for it in range(3):
    improved = False
    for key, vals in NEIGHBORS.items():
        for v in vals:
            if v == best[key]:
                continue
            cand = dict(best); cand[key] = v
            rn, ro = ev(cand)
            s = score(rn, ro)
            if s > bs:
                best, brn, bro, bs = cand, rn, ro, s
                improved = True
                print(f"  iter{it} {key}={v}: new {rn['pnl_usdc']:+.2f} old {ro['pnl_usdc']:+.2f} trades {rn['trades']}/{ro['trades']} dd {rn['max_dd']:.4f}/{ro['max_dd']:.4f} score {s:.2f}")
    if not improved:
        print(f"converged after iter {it}")
        break
print("\nFINAL:", json.dumps(best))
rn, ro = ev(best)
print(f"NEW: pnl {rn['pnl_usdc']:+.4f} trades {rn['trades']} fees {rn['fees_usdc']:.4f} maxDD {rn['max_dd']:.6f}")
print(f"OLD: pnl {ro['pnl_usdc']:+.4f} trades {ro['trades']} fees {ro['fees_usdc']:.4f} maxDD {ro['max_dd']:.6f}")
json.dump(best, open("final_params.json", "w"), indent=1)
