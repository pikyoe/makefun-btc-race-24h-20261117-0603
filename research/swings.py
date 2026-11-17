"""Zigzag swings: how much up-move is there to capture, and how often?"""
import sys
sys.path.insert(0, ".")
from sim import load_bars

def zigzag(c, rev_bps):
    pts = []
    # state: 'up' means we are tracking a rising leg (extreme = max so far)
    # start by finding the first move of >= rev_bps in either direction
    extreme = c[0]; extreme_i = 0; mode = None
    for i in range(1, len(c)):
        if mode is None:
            if (c[i]-c[0])*10000//c[0] >= rev_bps:
                mode = 'up'; extreme, extreme_i = c[i], i
            elif (c[0]-c[i])*10000//c[0] >= rev_bps:
                mode = 'down'; extreme, extreme_i = c[i], i
            continue
        if mode == 'up':
            if c[i] > extreme:
                extreme, extreme_i = c[i], i
            elif (extreme-c[i])*10000//extreme >= rev_bps:
                pts.append((extreme_i, extreme, 'high'))
                mode = 'down'; extreme, extreme_i = c[i], i
        else:  # down
            if c[i] < extreme:
                extreme, extreme_i = c[i], i
            elif (c[i]-extreme)*10000//extreme >= rev_bps:
                pts.append((extreme_i, extreme, 'low'))
                mode = 'up'; extreme, extreme_i = c[i], i
    pts.append((len(c)-1, c[-1], 'end'))
    return pts

for name, kit in [("NEW", "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"),
                  ("OLD", "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit")]:
    bars = load_bars(kit)
    c = [b["c"] for b in bars]
    print(f"===== {name} =====")
    for rev in (50, 80, 100, 150):
        pts = zigzag(c, rev)
        ups = []
        for (i0, p0, _), (i1, p1, _) in zip(pts, pts[1:]):
            if p1 > p0:
                ups.append((p1-p0)*10000//p0)
        gross = sum(ups)
        net = sum(max(u-35, 0) for u in ups)
        print(f"  rev {rev}: {len(pts)-1} legs, {len(ups)} up-legs, up sizes {sorted(ups, reverse=True)[:14]}")
        print(f"     sum up = {gross} bps; perfect net (full size, 35bps/trade) = {net/100:.2f} USDC; up>=100: {sum(1 for u in ups if u>=100)}, >=150: {sum(1 for u in ups if u>=150)}, >=200: {sum(1 for u in ups if u>=200)}")
