# STRATEGY.md — Dip Ladder

## What the data said

The dev window (1,440 bars) is a low-volatility range-bound day: total
return +48.9bps, 1-min return stdev 6.4bps, max drawdown −211.9bps. The old
round's window is a falling/crash day: total −401bps, stdev 12.0bps.

Dip → forward-return analysis (dip measured from the 60-bar high):

- New window, dip ≥150bps: 60-min forward mean +55bps (88% of cases beat
  the ~26bps round-trip cost), 120-min forward +112bps (100%).
- New window, dip ≥180bps: 60-min forward +69bps (100%).
- Old window, dip ≥180bps: 60-min forward +198bps (74%) — deep dips bounce
  even on a crash day.
- But shallow dips and short horizons are weak: dip ≥100bps, 15-min forward
  mean is only +0.9bps. Entries need time to work; the bounce takes 30–120
  minutes, so exits must be patient.
- The 240-bar trend separates the regimes. Deep dips (≥150bps) bounce on
  BOTH windows when the 240-bar trend is very negative (< −150bps). But the
  new window's main money band (240-bar trend −150..−50bps) is the old
  window's worst band (mean −86bps, 0% success). So the regime filter is set
  to admit dips only while the 240-bar trend is ≥ −150bps, which keeps the
  range-bound dips and blocks the waterfall dips.
- A dip bought at a shallow level is deep underwater by the time the dip
  bottoms, and the bounce from the bottom barely gets it back to breakeven.
  So legs must scale in as the dip deepens (the ladder), and the deepest leg
  — bought nearest the bottom — is the one that wins.

## Cost structure (measured live from the fill model)

Round-trip cost by leg size (fee 4bps + slippage 2bps each way + impact):

| leg size | round-trip cost |
|---|---|
| $100 | ~15bps |
| $250 | ~18bps |
| $500 | ~23bps |
| $1,000 | ~35bps |

Impact scales with size, so small legs are cheaper per trade but a $250 leg
earning +150bps nets only ~$3.30. Full-size legs cost more per trade
(~35bps) but earn far more per winning bounce. The ladder therefore uses
full-size legs (100% of equity each, capped by the 100% position limit),
trading sequentially: at most one full-size leg is open at a time in
practice, and the next leg opens after the previous one exits.

## Rules

### Entry (all must hold)

- `dip = (60-bar high − close) / 60-bar high ≥ 100bps`
- `trend60 = (close − close[60]) / close[60] ≤ 0bps` — no buying into a
  rising market's pullback (a dip there is a distribution top).
- `trend240 = (close − close[240]) / close[240] ≥ −150bps` — regime filter
  (see above); no upper bound.
- `mom5 = (close − close[5]) / close[5] ≥ 0bps` — don't buy while the price
  is still falling over the last 5 bars.
- Volatility sizing: realised 60-bar 1-min stdev above 8bps shrinks the leg
  (factor `8²/vol²`, floored at 50%). On the crash-day window (stdev ~12bps)
  legs are half size.
- Ladder spacing: a new leg needs the dip to have deepened by 40bps since
  the last leg, or 10 bars to have passed.
- No new legs after bar 1320 (last 2 hours); the bot only manages exits.
- Fallback: if no buy has filled by bar 1080, take a relaxed trade
  (dip ≥60bps, trend60 ≤ +50bps, half size) so the entry still makes ≥1
  trade (the race guardrail).

### Exit (per leg, checked every bar)

- Take-profit: close ≥ entry × (1 + 200bps).
- Two-stage trailing stop: while the leg's peak gain is below +140bps there
  is effectively no stop (the leg may ride through its wobble — a stop
  there only locks in losses, which the old-window test confirmed: adding a
  120–250bps stop turned the old window from +6.05 to −23..−32). Once the
  peak gain reaches +140bps, a tight 20bps trail below the peak engages and
  locks in the bounce instead of giving it back on the way down.
- Drawdown guard: if equity falls 4% below its peak, no new buys (existing
  legs are still managed to their exits).

### Parameters (all round values)

| parameter | value |
|---|---|
| LOOKBACK (rolling-high window) | 60 bars |
| DIP1_BPS (first leg) | 100 |
| DIP_STEP_BPS | 40 |
| MAX_LEGS | 3 |
| LEG_FRACTION_BPS | 10000 (full size) |
| TP_BPS | 200 |
| TRAIL_BPS (loose, while unarmed) | 10000 (off) |
| TRAIL_ARM_BPS | 140 |
| TRAIL_TIGHT_BPS | 20 |
| TREND_MAX_BPS (60-bar) | 0 |
| TREND240_MIN_BPS | −150 |
| TREND240_MAX_BPS | 10000 (off) |
| VOL_HIGH_BPS | 8 |
| VOL_MIN_FACTOR_BPS | 5000 (50%) |
| DD_GUARD_BPS | 400 (4%) |
| MIN_SEP_BARS | 10 |
| MOM_BARS / MOM_MIN_BPS | 5 / 0 |
| NO_NEW_AFTER_BAR | 1320 |
| FALLBACK_BAR / DIP / TREND_MAX | 1080 / 60 / +50 |
| MAX_SLIP_BPS | 300 |

## Validation

- **Exact offline simulator** (`research/sim.py`) replicates the kit's
  `sim/bars/engine.ts` fill math with Python ints. Validated against the
  kit's `grade-local` (process driver) on the new window for three reference
  strategies — buy-and-hold +1.067187, momentum +2.445627, rsi-bollinger
  −24.252523 — all matching to the micro-USDC.
- **New dev window:** +32.46 USDC, 6 trades, fees 1.63, max drawdown 0.74%.
- **Old round's dev window (crash day):** +6.05 USDC, 4 trades, fees 0.80,
  max drawdown 4.36%. Both clear the dev gate (net PnL > 0) and are far
  under the 25% max-drawdown limit.
- **Sensitivity:** varying each key parameter ±20% keeps the dev-window PnL
  positive in all 26 variations (+13.69 to +32.83 USDC). No knife-edge on the
  dev window.
- **Wire test:** `main.py` run as a subprocess over the real
  `agent-fun/bars-replay/v1` protocol (hello + 1,440 batches + done) exits 0
  with no stderr, 0 rejected orders, and two runs produce byte-identical
  action logs (sha256 match). The wire-test PnL equals the simulator PnL
  exactly (+32.455445).
- **Docker note:** `grade-local --driver docker` could not run on this VM:
  the daemon cannot create containers here (`setns: operation not permitted`
  — the cell forbids nested mount namespaces), even though the pinned
  `python:3.13-slim` image was fetched and is present. The exact simulator
  above is the validation path used instead; it is byte-exact against
  `grade-local` on the reference strategies.

## Honest caveats

- The old (crash-day) window result (+6.05) rests on only 4 trades, so it
  is sensitive to loosening the entry filters: DIP1 100→80 flips it to
  −35.74, TREND240_MIN −150→−180 flips it to −28.29, MIN_SEP 10→8 flips it
  to −6.24. The dev window is unaffected by those changes (all positive).
  The entry filters are set where they are precisely because loosening them
  admits waterfall trades on a crash day. A race day that trends hard down
  for hours will trade little or nothing, which is the intended behaviour
  (survive) rather than a failure mode.
- The 20bps tight trail is the single most valuable parameter (it is what
  lifts the dev PnL from ~+21 to ~+32); it is a smooth plateau, not a spike
  (TIGHT 10–50 all give +27.65 to +32.46 on the dev window), but it does
  assume the 1-min noise stays near the dev window's 6.4bps stdev.
- The dev-window PnL (+32.46) is below the leaderboard's top dev scores
  (39–50). It is a competitive, robust entry, not the maximum achievable:
  the theoretical perfect-foresight bound on this window is ~$60, and the
  extra $8–18 would require trading the small oscillations far more
  aggressively, which the old-window test shows does not survive a trending
  day.
