"""Dip episodes: contiguous stretches where dip-from-60bar-high >= thr."""
import sys
sys.path.insert(0, ".")
from sim import load_bars

def episodes(bars, thr=100):
    c = [b["c"] for b in bars]
    n = len(c)
    dips = []
    for i in range(60, n):
        hi = max(c[i-60:i+1])
        dips.append((hi - c[i]) * 10000 // hi)
    eps = []
    i = 0
    while i < len(dips):
        if dips[i] >= thr:
            j = i
            while j < len(dips) and dips[j] >= thr:
                j += 1
            # episode bars i..j-1 (bar index = i+60)
            seg = dips[i:j]
            start_bar = i + 60
            end_bar = j - 1 + 60
            maxdip = max(seg)
            # forward 120m return from episode end and from max-dip bar
            k_max = i + seg.index(maxdip) + 60
            fwd_end = (c[min(end_bar+120, n-1)] - c[end_bar]) * 10000 // c[end_bar] if end_bar+120 < n else None
            fwd_max = (c[min(k_max+120, n-1)] - c[k_max]) * 10000 // c[k_max] if k_max+120 < n else None
            eps.append((start_bar, end_bar, len(seg), maxdip, fwd_end, fwd_max))
            i = j
        else:
            i += 1
    return eps

for name, kit in [("NEW", "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"),
                  ("OLD", "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit")]:
    bars = load_bars(kit)
    for thr in (80, 100, 120, 150):
        eps = episodes(bars, thr)
        print(f"{name} thr={thr}: {len(eps)} episodes")
        for e in eps:
            print(f"   bars {e[0]}-{e[1]} len {e[2]} maxdip {e[3]} fwd120_from_end {e[4]} fwd120_from_maxdip {e[5]}")
