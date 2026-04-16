# LESSONS.md — IMC Prosperity 4: Cross-Round Learnings

Lessons from implementation, debugging, and analysis sessions.
Update this file after each round. Read before starting a new round's strategy.

---

## Round 1 Learnings

### L1. Understand the platform test window before interpreting results

The platform "Test" button runs **1,000 iterations** (ts 0–99,900), not the full 10,000.
This means:
- Phase-based strategies appear dramatically different in the test vs actual scoring
- A trend-rider that buys in Phase 1 (ts < 150k) looks great in the test (all buying, MtM rising)
- The full scoring run will show the complete cycle: buy → hold → sell
- **Always extrapolate**: multiply test PnL by 10, then apply phase-mix correction

```
Full-day estimate = test_pnl × 10 × phase_correction
# For a trend rider: phase_correction ≈ 0.85–0.95
```

---

### L2. The "EMA lag on trending assets" trap

Using a slow EMA as fair value for a strongly trending asset causes systematic losses.

**What happens:**
1. Price is trending up +1 per ts
2. EMA with alpha=0.08 lags behind by ~10–20 ts worth of drift
3. Fair value = EMA is below actual price
4. Passive ask = EMA + spread → always at or below actual price → bots never buy from us
5. Passive bid = EMA - spread → below actual bid → never catches fills from below
6. Net effect: we trade into the trend instead of with it

**Fix**: For strongly trending products, **do not use EMA as fair value for quoting**.
Instead, use a phase-based strategy: buy early, hold, sell late. Only use EMA for reference.

---

### L3. The Phase 3 short-position bug pattern

**Symptom**: At end of simulation, position is -80 instead of 0.

**Cause**: Using `sell_cap = limit + pos` in Phase 3 allows selling UP TO `limit + pos` units.
If pos=0 (position already flat), sell_cap = 80 → we open a short on a rising asset = disaster.

**Wrong:**
```python
sell_cap = limit + pos  # allows shorting even when pos=0
for bid in sorted(...):
    ...sell up to sell_cap...
```

**Correct:**
```python
close_qty = max(0, pos)  # only sell what we already hold; never go short
for bid in sorted(...):
    ...sell up to close_qty...
```

**Rule**: For one-directional trend strategies, Phase 3 should ONLY close longs, never open shorts.
Gate all sell logic with `if pos > 0`.

---

### L4. Simulator conservatism — do not over-tune to local backtest numbers

Our local simulator counts only immediate (aggressive) fills.
The actual platform ALSO fills passive quotes when bots trade against them next iteration.

**Implication**: Local backtest will consistently understate true PnL by ~20–35%.
```
platform_PnL ≈ local_backtest × 1.3
```

This is NOT a bug in the simulator — it is a deliberate conservative estimate.
Do not "fix" the simulator to match platform. Use it only as a relative comparison tool
("version A is better than version B") not as an absolute PnL predictor.

---

### L5. First-principles price analysis beats premature complexity

Before writing any algorithm, spend 10 minutes on the CSV data:
```python
import csv
prices = [float(row["mid_price"]) for row in csv.DictReader(open("prices.csv"), delimiter=";")]
print(f"mean={sum(prices)/len(prices):.1f}, min={min(prices)}, max={max(prices)}")
print(f"day0={prices[0]:.1f}, day_end={prices[-1]:.1f}, drift={prices[-1]-prices[0]:.1f}")
```

For Round 1, this revealed the exact trend (+1000/day) in 5 minutes.
A trend that clean does NOT need a momentum signal, Kalman filter, or ML model.
The simpler the signal, the harder it is to code incorrectly.

**Hierarchy of fair value approaches** (prefer simpler when sufficient):
1. Hardcoded constant (OSMIUM = 10000) — use when price is literally stable
2. Simple linear trend (PEPPER = start + rate * ts) — use when trend is clear and constant
3. EMA tracking — use only when trend is noisy or unknown
4. Complex statistical model — almost never needed for this competition

---

### L6. Bot spread calibration for passive quote placement

Bots in this competition quote with a consistent half-spread. Measure it from the CSV:
```python
spreads = []
for row in reader:
    b1, a1 = float(row["bid_price_1"]), float(row["ask_price_1"])
    spreads.append(a1 - b1)
avg_half_spread = sum(spreads) / len(spreads) / 2
```

Once you know the bot half-spread:
- **Aggressive orders**: price must CROSS the bot's best quote (bid > bot_ask, ask < bot_bid)
- **Passive quotes inside bot spread**: bots will fill us in future iterations
- **Passive quotes outside bot spread**: bots will never fill us (our quote is worse than theirs)

For Round 1:
- OSMIUM bot half-spread ≈ 8 → our quotes at ±3 are INSIDE → passive fills happen
- PEPPER bot half-spread ≈ 7.5 → our Phase 1 bid at fv+7 is INSIDE (barely) → fills happen

---

### L7. traderData sizing — simpler is better

Avoid storing price history in traderData for iterative strategies.
For the EMA pattern, only the current EMA value needs to be stored (1 float = ~34 chars).
Storing 100 price points would add ~1,200 chars for no benefit when online algorithms exist.

```python
# BAD: stores O(N) history
data["pepper_prices"] = data.get("pepper_prices", []) + [mid]

# GOOD: online algorithm, O(1) storage
data["pepper_ema"] = alpha * mid + (1 - alpha) * data.get("pepper_ema", mid)
```

Use Welford's online algorithm for running mean/std instead of storing lists.

---

### L8. Position limit silent cancellation — test it explicitly

The exchange silently cancels ALL orders if ANY order would breach the limit.
This means a single oversized order wipes out your entire order set for that iteration.

Test for this in backtesting by printing fills per iteration. If you see iterations with
zero fills but your logic clearly should be filling, you likely have a limit breach.

Pattern to audit:
```python
# Dangerous: aggressive + passive orders can sum to > limit
aggressive_qty = ...  # e.g. fills 70 units
passive_qty = limit - pos  # also 80 units
# Total attempted: 150 → BREACH → all cancelled
```

Fix: track `buy_cap` across both aggressive and passive order generation:
```python
buy_cap = limit - pos
# After aggressive fills:
buy_cap -= aggressive_qty
# Then use buy_cap for passive orders:
orders.append(Order(product, bid_price, buy_cap))  # always safe
```

---

## Workflow Learnings

### W1. Analysis → Strategy → Code → Backtest loop

The most effective workflow for each new product:

1. **Analyze CSV** (5–10 min): plot or compute basic stats (mean, std, drift, bot spread)
2. **Classify**: stable / trending / oscillating → pick strategy family
3. **Define exact parameters** before writing code: fair_value, spread, thresholds, phases
4. **Implement** in ~100–150 lines — no over-engineering
5. **Backtest** locally — verify positive PnL across all 3 days
6. **Compare versions** by running both and checking delta — never submit without comparison

### W2. Version archiving discipline

Every backtest-confirmed version gets archived immediately:
```bash
cp src/trader.py submissions/round{N}/trader_v{N}.py
```

This makes rollback trivial when a "improvement" turns out to hurt PnL.
Name format: `trader_v1.py`, `trader_v2.py`, etc.

### W3. Read the platform debug logs

After each platform test, download the debug log (dashboard → test result → download).
It shows per-iteration fills, positions, and PnL breakdown by product.
This is far more informative than the graph alone.

---

## Round 2 Pre-Read

Before starting Round 2:
- [ ] Check what products are introduced (dashboard after round opens)
- [ ] Download new CSV data files to `backtesting/data/ROUND2/`
- [ ] Run the same quick stats analysis on new products
- [ ] Update `bid()` method — research the auction mechanic in Round 2 wiki
- [ ] The `bid()` method participates in a one-shot sealed-bid auction for some resource
      Check the wiki for current round's auction rules before submitting a value
