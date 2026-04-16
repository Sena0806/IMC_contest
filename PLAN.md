# PLAN.md — IMC Prosperity 4 Master Execution Plan

**Created**: 2026-04-15  
**PM**: Claude (Genius Project Manager Mode)  
**Goal**: Top leaderboard. Every XIREC counts.

---

## Win Condition

- **Primary**: Maximize total PnL across all 5 rounds
- **Gate**: ≥ 200,000 XIRECs by end of Round 2 (required to advance to Rounds 3-5)
- **Stretch**: Top 25 globally

---

## Critical Path

```
[Setup Infra] → [Implement Core Strategy] → [Backtest] → [Submit R1]
                        ↓
              [Analyze R1 Results] → [Refine] → [Submit R2]
                        ↓
              [Intermission: Deep Optimization] → [Submit R3-R5]
```

The single biggest lever: **how good is our fair value estimate**.
Everything — market making spread, mean reversion entry, aggression — depends on knowing where fair value is.

---

## Sprint 0 — Infrastructure (TODAY, 4/15, ~4 hours)

**Goal**: Working dev environment, can run code locally.

### Tasks

- [ ] Copy `datamodel.py` from Wiki Appendix B into `src/datamodel.py`
- [ ] Build `backtesting/simulator.py` — minimal harness that replays CSV data and calls `Trader.run()`
- [ ] Create `scripts/build.py` — concatenates strategy modules into single `trader.py`
- [ ] Create `src/trader.py` skeleton with `Trader` class, `bid()`, `run()`, state load/save pattern
- [ ] Confirm: `python src/trader.py` runs without errors

### Deliverable

`python backtesting/simulator.py --data backtesting/data/sample.csv` outputs PnL without crashing.

---

## Sprint 1 — Round 1 Core Strategy (4/15 evening – 4/17 11:00)

**Deadline**: Submit before **4/17 12:00 CEST**. Target submit by **4/17 10:00** (2-hour safety margin).

### Step 1: Understand the Products (30 min)

1. Log into dashboard → check A.R.I.A. Uplink video for Round 1
2. Note: which products are active, their position limits
3. Download CSV data from Data Capsule
4. Quick visual inspection: is price stable, oscillating, or trending?
5. Fill in the product table in `SKILLS.md` Section 11

### Step 2: Implement Strategy Per Product (3-4 hours)

**Default starting point for every product: Market Making + Aggressive Taker**

```
For each product:
1. Estimate fair value (use mid-price or EMA)
2. Aggressively take any orders clearly mispriced vs fair value
3. Post passive market-making quotes around fair value
4. Apply inventory skew to keep position near 0
```

Files to implement:
- `src/strategies/market_maker.py` — generic market making logic
- `src/strategies/fair_value.py` — fair value estimation per product
- `src/risk/position_manager.py` — position clamping utility
- `src/utils/state.py` — traderData load/save helpers

### Step 3: Backtest (1 hour)

- Run simulator on all available CSV data
- Verify PnL > 0 for each product
- Check no position limit violations
- Measure average `run()` time (must be << 900ms)

### Step 4: Build + Archive + Submit

```bash
python scripts/build.py                          # → src/trader.py (merged)
cp src/trader.py submissions/round1/trader_v1.py
# Upload to dashboard, mark as active
```

### Step 5: Iterate Until Deadline

After first submission, keep improving:
- Tune spread width
- Tune EMA alpha
- Add mean reversion signal if data supports it
- Each improvement: backtest → build → archive with version number → re-upload

---

## Sprint 2 — Round 2 (4/17 12:00 – 4/20 12:00)

**Special requirement**: `bid()` method is active this round.

### What `bid()` does

Round 2 has a special auction mechanic where `bid()` returns a single integer bid price.
Research the mechanic from A.R.I.A. Uplink at round start. Optimal bid depends on:
- Distribution of other participants' bids (unknown, but can estimate)
- Value of the auctioned item
- Game-theoretic reasoning: bid slightly above expected median, not max

### Tasks

- [ ] Watch A.R.I.A. Uplink for Round 2 mechanics
- [ ] Understand what is being auctioned and what the payoff structure is
- [ ] Determine optimal `bid()` return value
- [ ] Continue refining Round 1 strategies (same products likely available)
- [ ] Add any new products introduced in Round 2

### Goal

Confirm ≥ 200,000 XIRECs total → **mission success, access to Rounds 3-5**.

---

## Intermission (4/20 – 4/24) — Deep Optimization

**This is the most valuable time in the contest.** No deadline pressure. Use it fully.

### Priority 1: Analyze Round 1 & 2 Results

- Download debug logs from dashboard
- Calculate per-product PnL breakdown
- Identify: which products were profitable, which lost money, why
- Review `own_trades` patterns: are we trading at good prices?

### Priority 2: Strategy Refinement

Based on analysis, implement improvements:

| Weakness Found | Fix |
|----------------|-----|
| Position drifting to limit and getting stuck | Stronger inventory skew, add position-unwind orders |
| Missing profitable bot orders | Lower aggression threshold |
| Spread too wide → few fills | Tighten spread |
| Spread too tight → adverse selection | Widen spread, use order flow signal |
| Mean reversion loss → actually trending | Switch to momentum |

### Priority 3: New Capabilities

- [ ] Implement `OnlineStats` (Welford) for rolling mean/std without buffer
- [ ] Implement order flow imbalance signal (OFI) as fair value adjustment
- [ ] Implement conversion arbitrage if relevant products exist
- [ ] Add logging to `traderData` for post-round analysis

### Priority 4: Testing Infrastructure

- [ ] Pytest suite with at least 10 unit tests covering core logic
- [ ] Parametric backtest: sweep spread values, pick optimal
- [ ] Regression test: ensure refactors don't degrade PnL

---

## Sprints 3-5 — Rounds 3-5 (4/24 – 4/30)

Each round: new products may be introduced. Apply the same process:

```
1. A.R.I.A. Uplink → understand new products
2. Download data → analyze price behavior
3. Pick strategy per product
4. Implement + backtest
5. Submit early, iterate until close
```

### Round-Specific Notes

- **Round 3-4**: More complex products expected. Likely arbitrage or conversion opportunities.
- **Round 5**: Final round — maximize aggression on profitable strategies. Less concern about risk if PnL cushion is large.

---

## Strategy Priority Stack

Apply in this order. Stop when signals conflict:

```
1. TAKE mispriced orders immediately (highest priority, free money)
2. POST market-making quotes around fair value
3. SKEW quotes based on inventory
4. UNWIND position if near limit and no good opportunities
```

---

## Risk Management Rules

| Rule | Detail |
|------|--------|
| Never exceed position limit | Clamp all orders before returning |
| Target position = 0 at end | Skew quotes to naturally revert |
| Max traderData size | Keep under 45k chars (buffer for 50k limit) |
| Execution time | No computation > O(n) where n = order book depth |
| No external libraries | pandas, numpy, statistics, math, typing, jsonpickle only |

---

## File Naming Convention

```
submissions/
├── round1/
│   ├── trader_v1.py     # First working submission
│   ├── trader_v2.py     # After backtest improvements
│   └── trader_vFINAL.py # Last uploaded version
├── round2/
│   └── ...
```

Always increment version. Never overwrite. This allows rollback and analysis.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-15 | Market Making as default strategy | Most reliable for unknown products; earns spread regardless of direction |
| 2026-04-15 | Single-file build script | Submission requires single .py file but modular dev is necessary |
| 2026-04-15 | State via traderData JSON | AWS Lambda stateless; class vars unreliable |
| 2026-04-15 | EMA for fair value | Smooths noise while tracking drift; simple and fast |

---

## Open Questions (resolve at start of each round)

- What are the products in this round?
- What are their position limits?
- Is this product trending, oscillating, or stable?
- Are there cross-product relationships to exploit?
- Is conversion arbitrage available?
- What does `bid()` need to return this round?

---

## Useful Commands

```bash
# Build single submission file
python scripts/build.py

# Run local backtest
python backtesting/simulator.py --data backtesting/data/round1_prices.csv

# Run tests
pytest tests/ -v

# Check traderData size
python -c "import jsonpickle; d = {...}; print(len(jsonpickle.encode(d)))"

# Archive submission
cp src/trader.py submissions/round1/trader_v$(date +%H%M).py
```
