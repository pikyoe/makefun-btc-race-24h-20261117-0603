"""End-to-end wire test: run main.py as a subprocess over the real protocol,
driven by the exact simulator's fill math. Verifies: valid replies, correct
seq echo, order encoding accepted by the shim, and byte-identical action logs
across two runs (determinism)."""
import json, subprocess, sys, hashlib
sys.path.insert(0, ".")
sys.path.insert(0, "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603")
from sim import load_bars, Sim

KIT = "/home/hatch/workspace/makefun-watch/batch2/kits/btc-race-24h-20261117-0603/btc-race-24h-20261117-0603-kit"
BARS = load_bars(KIT)
HELLO = {
    "type": "hello", "protocol": "agent-fun/bars-replay/v1",
    "capital": {"quote_units": "1000000000", "quote_scale": 6},
    "symbols": [{"symbol": "CBBTC", "qty_scale": 8, "price_scale": 5}],
    "caps": {"max_orders_per_bar": 16, "max_weight_bps": 10000,
             "max_open_positions": 1, "min_notional_quote_units": 1000000,
             "fee_bps": 4, "slippage_bps": 2},
    "seed": 20261117,
}

def run_once():
    proc = subprocess.Popen(
        ["python3", "-P", "-s", "/home/hatch/workspace/makefun-btc-race-24h-20261117-0603/main.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    replies = []
    proc.stdin.write(json.dumps(HELLO) + "\n"); proc.stdin.flush()

    def proxy_on_batch(state, batch):
        i = batch["seq"]
        bar = BARS[i]
        pos = [{"symbol": "CBBTC", "qty": str(h.qty), "cost_quote_units": str(h.cost)}
               for h in state.positions.values()]
        wire = {
            "type": "batch", "seq": i, "t": bar["t"],
            "bars": [{"symbol": "CBBTC", "o": str(bar["o"]), "h": str(bar["h"]),
                      "l": str(bar["l"]), "c": str(bar["c"]),
                      "o_depth": [str(d) for d in bar["o_depth"]],
                      "c_depth": [str(d) for d in bar["c_depth"]]}],
            "account": {"cash_quote_units": str(state.cash),
                        "equity_quote_units": str(state.equity),
                        "positions": pos},
            "fills": batch["fills"],
        }
        proc.stdin.write(json.dumps(wire) + "\n"); proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"bot exited early at seq {i}: stderr={proc.stderr.read()[:800]}")
        replies.append(line)
        msg = json.loads(line)
        assert msg.get("type") == "reply", f"bad reply type {msg}"
        assert msg.get("seq") == i, f"seq mismatch {msg.get('seq')} != {i}"
        return msg.get("orders") or []

    sim = Sim(BARS, proxy_on_batch)
    result = sim.run()
    proc.stdin.write(json.dumps({"type": "done", "seq": len(BARS),
        "account": {"cash_quote_units": str(int(result["final_cash_usdc"] * 1_000_000)),
                    "equity_quote_units": str(int(result["final_cash_usdc"] * 1_000_000)),
                    "positions": []}}) + "\n")
    proc.stdin.flush()
    proc.wait(timeout=30)
    err = proc.stderr.read()
    return result, replies, proc.returncode, err

r1, rep1, code1, err1 = run_once()
r2, rep2, code2, err2 = run_once()
print("run1 result:", r1, "exit", code1, "stderr:", err1[:200])
print("run2 result:", r2, "exit", code2, "stderr:", err2[:200])
h1 = hashlib.sha256("".join(rep1).encode()).hexdigest()
h2 = hashlib.sha256("".join(rep2).encode()).hexdigest()
print("replies run1:", len(rep1), "run2:", len(rep2))
print("action-log sha256 run1:", h1)
print("action-log sha256 run2:", h2)
print("BYTE-IDENTICAL ACTION LOGS:", h1 == h2)
print("total orders in run1:", sum(len(json.loads(l)["orders"]) for l in rep1))
print("replies with orders:")
for l in rep1:
    m = json.loads(l)
    if m["orders"]:
        print("  seq", m["seq"], json.dumps(m["orders"]))
