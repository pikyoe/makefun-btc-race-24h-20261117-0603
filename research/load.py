"""Load CBBTC bars from a kit dataset."""
import gzip, json, os

def load_bars(kit_dir):
    path = os.path.join(kit_dir, "dataset/bars/CBBTC.ndjson.gz")
    bars = []
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.strip()
            if line:
                bars.append(json.loads(line))
    return bars

def summarize(bars, name):
    o = [int(b["o"]) for b in bars]
    c = [int(b["c"]) for b in bars]
    h = [int(b["h"]) for b in bars]
    l = [int(b["l"]) for b in bars]
    n = len(bars)
    print(f"--- {name}: {n} bars ---")
    print("first close", c[0], "last close", c[-1], "total ret bps", (c[-1]-c[0])*10000//c[0])
    print("min close", min(c), "max close", max(c))
    import statistics
    rets = [(c[i]-c[i-1])*10000//c[i-1] for i in range(1, n)]
    print("1m ret stdev bps %.2f mean %.3f" % (statistics.pstdev(rets), statistics.mean(rets)))
    # 30-min returns
    r30 = [(c[i]-c[i-30])*10000//c[i-30] for i in range(30, n)]
    print("30m ret min %d max %d" % (min(r30), max(r30)))
    # bars >= 150bps below 60-bar high
    cnt150 = 0
    for i in range(60, n):
        hi = max(c[i-60:i+1])
        if (hi-c[i])*10000//hi >= 150:
            cnt150 += 1
    print("bars >=150bps below 60-bar high:", cnt150)
    # 4h block returns
    for b in range(6):
        s, e = b*240, min((b+1)*240, n)
        print(f"  block {b} ({s}-{e}): {(c[e-1]-c[s])*10000//c[s]} bps")
    # depth stats
    import statistics as st
    od = [int(b["o_depth"][0]) for b in bars]
    print("o_depth min %d median %d max %d (raw units)" % (min(od), st.median(od), max(od)))
    print("first bar keys:", sorted(bars[0].keys()))
    print("first bar:", {k: bars[0][k] for k in bars[0]})
    return bars

if __name__ == "__main__":
    new_kit = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
    old_kit = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261115-0828/btc-race-24h-20261115-0828-kit"
    b_new = load_bars(new_kit)
    summarize(b_new, "NEW dev window")
    b_old = load_bars(old_kit)
    summarize(b_old, "OLD dev window")
