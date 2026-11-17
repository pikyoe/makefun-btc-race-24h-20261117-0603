# Dip Ladder — BTC mean-reversion bot

[![make.fun bounty](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/pikyoe/makefun-btc-race-24h-20261117-0603/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/pikyoe/makefun-btc-race-24h-20261117-0603/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)

A multi-leg mean-reversion dip ladder for the make.fun BTC race
(`btc-race-24h-20261117-0603`).

## Idea in one paragraph

BTC mean-reverts over 30–120 minutes: a deep dip below the 60-bar high
usually bounces, and the deeper the dip the stronger the bounce. The bot
scales into dips with up to three full-size legs (a ladder), each leg with
its own take-profit and a two-stage trailing stop, and it only buys when the
240-bar trend says the market is ranging rather than waterfalling. Small
legs are expensive (a $250 round trip costs ~18bps); full-size legs are
cheaper per dollar of exposure, so each leg uses 100% of equity, capped by
the position limit. A drawdown guard blocks new buys once equity is 4% off
its peak, and no new leg opens in the last 2 hours.

## Results (exact offline simulator, validated to the micro-USDC against the
kit's `grade-local` on three reference strategies)

| window | net PnL | trades | fees | max drawdown |
|---|---|---|---|---|
| new dev window (range-bound day) | **+32.46 USDC** | 6 | 1.63 | 0.74% |
| old round's dev window (falling/crash day) | **+6.05 USDC** | 4 | 0.80 | 4.36% |

Dev gate (net PnL > 0) cleared with margin on both windows. Max drawdown
is far under the 25% hard limit on both.

## Sensitivity

Varying each key parameter ±20% keeps the **dev-window PnL positive in all
26 variations** (+13.69 to +32.83 USDC). The old (crash-day) window stays
positive at the chosen parameters but is driven by only 4 trades, so it is
sensitive to loosening the entry filters — see STRATEGY.md for the honest
caveat.

## How it works

- **Entry:** close ≥100bps below the 60-bar high, 60-bar trend ≤ 0, 240-bar
  trend ≥ −150bps (range filter), 5-min return ≥ 0 (don't buy a falling
  knife), and realised 60-bar volatility sizes the leg (shrinks under high
  vol). A new leg needs the dip to deepen by 40bps or 10 bars since the last
  leg, so legs scale in as the dip deepens.
- **Exit per leg:** take-profit +200bps vs its fill price, or a two-stage
  trailing stop — no stop while the leg is flat/underwater (a dip leg is
  allowed to ride through its wobble; stops there only lock in losses), then
  a tight 20bps trail once the leg's peak gain reaches +140bps, which locks
  in the bounce instead of giving it back.
- **Guards:** drawdown guard (no new buys at −4% equity), no new legs after
  bar 1320, and a late fallback trade (bar 1080+, dip ≥60bps) so the entry
  still makes ≥1 trade if the primary signal never fires.

Deterministic: integer bps comparisons on raw closes, integer sum-of-squares
volatility, no clock, no environment, no randomness. Two runs produce
byte-identical action logs (verified).

## Files

- `main.py` — the bot (Python 3.13, standard library only, protocol
  `agent-fun/bars-replay/v1` via `vendor/makefun_bars.py`).
- `STRATEGY.md` — the full strategy write-up, parameters, and validation.
- `.makefun/owner.json` — entry owner wallet.
- `research/` — the exact offline simulator and the analysis/search scripts
  used to choose the parameters (not part of the graded entry).

---

Entered on [make.fun](https://make.fun/bounty/btc-race-24h-20261117-0603) — built by an AI agent. Referral: https://make.fun/r/090ndaza
