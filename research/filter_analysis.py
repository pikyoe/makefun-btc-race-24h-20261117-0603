"""Forward returns after dip>=100, split by 240-bar trend and realized vol."""
import sys, math
sys.path.insert(0, ".")
from sim import load_bars

def analyze(bars, name):
    c = [b["c"] for b in bars]
    n = len(c)
    print(f"===== {name} =====")
    print("-- split by 240-bar trend at dip bar (dip>=100, fwd60) --")
    for tlo, thi in ((-10000,-300), (-300,-150), (-150,-50), (-50,50), (50,10000)):
        fwds = []
        for i in range(240, n-60):
            hi = max(c[i-60:i+1])
            dip = (hi-c[i])*10000//hi
            tr = (c[i]-c[i-240])*10000//c[i-240]
            if dip >= 100 and tlo <= tr < thi:
                fwds.append((c[i+60]-c[i])*10000//c[i])
        if fwds:
            import statistics as st
            print(f"  trend240 [{tlo},{thi}): n={len(fwds):3d} fwd60 mean {st.mean(fwds):+7.1f} med {st.median(fwds):+7.1f} frac>26: {sum(1 for x in fwds if x>26)/len(fwds):.2f}")
    print("-- split by realized vol (60-bar 1-min stdev, dip>=100, fwd60) --")
    for vlo, vhi in ((0,6), (6,9), (9,12), (12,100)):
        fwds = []
        for i in range(240, n-60):
            hi = max(c[i-60:i+1])
            dip = (hi-c[i])*10000//hi
            rets = [(c[j]-c[j-1])*10000//c[j-1] for j in range(i-59, i+1)]
            import statistics as st
            vol = st.pstdev(rets)
            if dip >= 100 and vlo <= vol < vhi:
                fwds.append((c[i+60]-c[i])*10000//c[i])
        if fwds:
            import statistics as st
            print(f"  vol [{vlo},{vhi}): n={len(fwds):3d} fwd60 mean {st.mean(fwds):+7.1f} med {st.median(fwds):+7.1f} frac>26: {sum(1 for x in fwds if x>26)/len(fwds):.2f}")
    print("-- split by dip depth AND 240-bar trend (fwd60) --")
    for tlo, thi in ((-10000,-150), (-150,10000)):
        for dlo, dhi in ((100,150),(150,10000)):
            fwds = []
            for i in range(240, n-60):
                hi = max(c[i-60:i+1])
                dip = (hi-c[i])*10000//hi
                tr = (c[i]-c[i-240])*10000//c[i-240]
                if dlo <= dip < dhi and tlo <= tr < thi:
                    fwds.append((c[i+60]-c[i])*10000//c[i])
            if fwds:
                import statistics as st
                print(f"  trend240 [{tlo},{thi}) dip [{dlo},{dhi}): n={len(fwds):3d} fwd60 mean {st.mean(fwds):+7.1f} med {st.median(fwds):+7.1f} frac>26: {sum(1 for x in fwds if x>26)/len(fwds):.2f}")

NEW = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
OLD = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
analyze(load_bars(NEW), "NEW")
analyze(load_bars(OLD), "OLD")
