# IMC Prosperity 4 — Trading Algorithm

Algorithmic trading competition by IMC. We write a Python `Trader` class that maximizes XIREC profit against market-making bots across 5 rounds.

**Platform**: [prosperity.imc.com](https://prosperity.imc.com/)
**Language**: Python 3.12 (single-file submission)
**Competition period**: Apr 14 – Apr 30, 2026

---

## Repository Layout

```
IMC_contest/
├── src/
│   ├── trader.py          ★ SUBMISSION FILE — upload this
│   └── datamodel.py       Official datamodel (do not modify)
├── backtesting/
│   ├── simulator.py       Local backtest harness
│   └── data/ROUND{N}/     CSV price data (download from dashboard)
├── submissions/
│   └── round{N}/          Archived submissions (trader_v1.py, v2.py …)
├── artifacts/
│   └── round{N}/          Platform test logs, result JSONs
├── tests/                 pytest unit tests
├── Prosperity 4 Wiki/     Offline copy of contest wiki
├── CLAUDE.md              AI assistant guidelines + project context
├── SKILLS.md              Trading strategy reference (read before implementing)
├── LESSONS.md             Cross-round learnings and bug patterns
└── PLAN.md                Master execution plan
```

---

## Quick Start

### Requirements

```bash
pip install jsonpickle
# Python 3.12 or 3.13 required (same as platform)
```

### Run Backtests

```bash
# All 3 days (Day -2, -1, 0)
python3.13 backtesting/simulator.py

# Single day
python3.13 backtesting/simulator.py --day 0

# With fill-by-fill logging
python3.13 backtesting/simulator.py --verbose
```

Expected output for Round 1 (conservative — actual platform PnL is ~30% higher):

```
  INTARIAN_PEPPER_ROOT            66,800+  per day
  ASH_COATED_OSMIUM                5,000+  per day
  ─────────────────────────────────────
  Total (3-day conservative)      216,651
```

### Run Tests

```bash
pytest tests/
```

---

## Submitting

1. Verify `src/trader.py` passes backtest above
2. Archive: `cp src/trader.py submissions/round{N}/trader_vX.py`
3. Upload `src/trader.py` to dashboard → Challenge Details → Upload Algorithm
4. Mark as **Active** — only the active file is scored

Re-upload as many times as needed before the round deadline.

---

## Round 1 Strategy Summary

| Product | Limit | Strategy | Expected PnL/day |
|---------|-------|----------|-----------------|
| `ASH_COATED_OSMIUM` | ±80 | Mean-reversion market maker around 10,000 | ~5,000+ XIREC |
| `INTARIAN_PEPPER_ROOT` | ±80 | Trend rider (+1,000/day drift) | ~66,800+ XIREC |

**PEPPER strategy**: Buy aggressively in first 15% of day → hold at max long → sell in last 15%.
**OSMIUM strategy**: Quote bid/ask at ±3 from fair value 10,000; aggress any ask < 9,998 or bid > 10,002.

See [SKILLS.md](SKILLS.md) for the full strategy reference and [LESSONS.md](LESSONS.md) for implementation gotchas.

---

## Round Schedule

| Round | Opens | Closes | Status |
|-------|-------|--------|--------|
| 1 | Apr 14 | Apr 17 12:00 CEST | Active |
| 2 | Apr 17 | Apr 20 12:00 CEST | Upcoming |
| 3 | Apr 20 | Apr 23 12:00 CEST | Upcoming |
| 4 | Apr 23 | Apr 26 12:00 CEST | Upcoming |
| 5 | Apr 26 | Apr 30 12:00 CEST | Upcoming |

---

## Key Constraints

| Constraint | Value |
|------------|-------|
| Submission format | Single `.py` file, `Trader` class with `run()` and `bid()` |
| Allowed imports | `pandas`, `numpy`, `statistics`, `math`, `typing`, `jsonpickle` + stdlib |
| `run()` time limit | < 900ms (target avg ≤ 100ms) |
| `traderData` size | < 50,000 chars |
| Position breach | Silently cancels ALL orders for that product |

---

## For Collaborators

### Adding a Strategy

1. Read [SKILLS.md](SKILLS.md) — strategy patterns are documented there
2. Analyze the product's CSV data first (mean, std, drift, bot spread)
3. Implement in `src/trader.py` under the appropriate `_trade_*` method
4. Run backtests — verify positive PnL on all 3 days before committing
5. Archive old version before overwriting: `submissions/round{N}/trader_vX.py`

### Improving an Existing Strategy

Before changing parameters:
- Run local backtest → note baseline PnL
- Change one parameter at a time
- Compare before/after PnL across all 3 days
- Only submit if all 3 days improve (or at least don't regress)

### Common Pitfalls

- **EMA lags on trending assets** → use phase-based strategy instead (see LESSONS.md L2)
- **Phase 3 shorting** → never use `sell_cap = limit + pos`; use `close_qty = max(0, pos)` (see LESSONS.md L3)
- **Silent position breach** → track `buy_cap`/`sell_cap` across all order generation (see LESSONS.md L8)
- **Platform test = 10% of a day** → 1,000 iterations covers ts 0–99,900 only; extrapolate ×10 for full-day estimate
