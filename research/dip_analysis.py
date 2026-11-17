"""Dip -> forward-return statistics on both windows."""
import sys
sys.path.insert(0, ".")
from sim import load_bars

def analyze(bars, name):
    c = [b["c"] for b in bars]
    n = len(c)
    print(f"===== {name} =====")
    for dip_thr in (60, 80, 100, 120, 150, 180):
        for horizon in (15, 30, 60, 120):
            fwds, max_dds, max_ups = [], [], []
            for i in range(60, n - horizon):
                hi = max(c[i-60:i+1])
                dip = (hi - c[i]) * 10000 // hi
                if dip >= dip_thr:
                    fwds.append((c[i+horizon] - c[i]) * 10000 // c[i])
                    seg = c[i:i+horizon+1]
                    max_dds.append((min(seg) - c[i]) * 10000 // c[i])
                    max_ups.append((max(seg) - c[i]) * 10000 // c[i])
            if fwds:
                import statistics as st
                print(f"dip>={dip_thr:3d}bps H={horizon:3d}m n={len(fwds):3d} "
                      f"fwd mean {st.mean(fwds):+7.1f} med {st.median(fwds):+7.1f} "
                      f"min {min(fwds):+5d} max {max(fwds):+5d} | "
                      f"worst further drop {min(max_dds):+5d} | best up {max(max_ups):+5d} | "
                      f"frac fwd>26bps: {sum(1 for x in fwds if x>26)/len(fwds):.2f}")
    # trend filter: 60-bar return at dip time vs forward return
    print("-- dip>=100, split by 60-bar trend --")
    for tlo, thi in ((-10000, -150), (-150, -50), (-50, 50), (50, 10000)):
        fwds = []
        for i in range(60, n - 60):
            hi = max(c[i-60:i+1])
            dip = (hi - c[i]) * 10000 // hi
            tr = (c[i] - c[i-60]) * 10000 // c[i-60]
            if dip >= 100 and tlo <= tr < thi:
                fwds.append((c[i+60] - c[i]) * 10000 // c[i])
        if fwds:
            import statistics as st
            print(f"  trend [{tlo},{thi}): n={len(fwds):3d} fwd60 mean {st.mean(fwds):+7.1f} med {st.median(fwds):+7.1f} frac>26: {sum(1 for x in fwds if x>26)/len(fwds):.2f}")

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
analyze(load_bars(NEW), "NEW window")
analyze(load_bars(OLD), "OLD window")
