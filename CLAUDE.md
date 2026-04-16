# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# IMC Prosperity 4 — Project Context

## Contest Overview

- **What**: Algorithmic trading competition. Write a Python `Trader` class that maximizes XIREC profit against bots.
- **Round 1 deadline**: 4/17 (Fri) 12:00 CEST — **URGENT**
- **Platform**: https://prosperity.imc.com/
- **Discord**: Official support channel

## Project Structure

```
IMC_contest/
├── CLAUDE.md              # This file
├── SKILLS.md              # Trading strategy reference
├── PLAN.md                # Master execution plan
├── LESSONS.md             # Cross-round learnings
├── src/
│   ├── trader.py          # ★ SUBMISSION FILE (merged single file)
│   ├── datamodel.py       # Official datamodel (do NOT modify)
│   ├── strategies/        # Strategy modules (merged into trader.py at submission)
│   ├── risk/              # Risk management modules
│   └── utils/             # Utility functions
├── backtesting/
│   ├── simulator.py       # Local test harness
│   ├── data/              # CSV files downloaded from dashboard
│   └── results/           # Backtest output logs
├── submissions/
│   └── round{N}/          # Archived submissions per round
├── artifacts/
│   └── round{N}/
│       └── dashboard_exports/   # Files downloaded from platform after each run
│           ├── round{N}_log_{run_id}.log        # print() output from your code
│           ├── round{N}_result_{run_id}.json    # full market data + PnL + positions
│           └── round{N}_submission_{run_id}.py  # exact code that ran
└── tests/                 # pytest unit tests
```

## Submission Rules

1. **File to upload**: `src/trader.py` — single Python file containing the `Trader` class
2. The file must be **self-contained** (no local imports other than `datamodel`)
3. Use `scripts/build.py` to merge strategy modules into a single `trader.py` before upload
4. Upload via dashboard → "Challenge Details" → "Upload Algorithm" → drag & drop
5. Mark the file as **"active"** — only the active file counts
6. You can re-upload as many times as you want before the deadline
7. Round 2 requires a `bid()` method on the Trader class — include it in all submissions

## Architecture Decisions

### Single-File Build

Develop in modular files under `src/strategies/`, `src/risk/`, `src/utils/`.
Before submission, use `scripts/build.py` to concatenate into a single `trader.py`.
This keeps development clean without sacrificing the submission requirement.

### State Persistence

AWS Lambda is stateless — class variables are NOT guaranteed to persist between calls.
Always use `traderData` (JSON string, max 50k chars) for state:

```python
import jsonpickle

# Save state at end of run()
state_dict = {"prices": self.price_history, "position_ewm": self.ewm}
traderData = jsonpickle.encode(state_dict)

# Restore state at start of run()
if state.traderData:
    data = jsonpickle.decode(state.traderData)
```

### Per-Product Strategy

Each product gets its own strategy instance. The `Trader.run()` dispatches per product:

```python
STRATEGIES = {
    "RAINFOREST_RESIN": MarketMaker(fair_value=10000, spread=2, limit=50),
    "KELP": MeanReversion(window=20, limit=50),
}
```

### Position Limits

Always check position before sending orders. Orders that would breach limits are **silently cancelled** by the exchange — causing missed trades, not errors.

```python
remaining_buy  = limit - current_pos
remaining_sell = limit + current_pos  # limit is absolute
```

## Supported Libraries Only

`pandas`, `numpy`, `statistics`, `math`, `typing`, `jsonpickle` + Python 3.12 standard library.
No other external imports. Violations cause silent submission failure.

## Performance Constraint

Each `run()` call must complete in **< 900ms**. Average should be ≤ 100ms.
No heavy computation inside `run()`. Pre-compute where possible, or use lightweight online algorithms.

## Testing Protocol

Before every submission:
1. Run `python backtesting/simulator.py` on local CSV data → check PnL is positive
2. Run `pytest tests/` → all tests pass
3. Check `traderData` size stays under 50,000 chars
4. Archive the file to `submissions/round{N}/trader_v{version}.py`
5. Upload and mark as active

## Environment Notes

### Python Version

The system has multiple Python installations. Use the explicit path to avoid version mismatch:

```bash
# WRONG — system python3 is 3.9, no jsonpickle
python3 backtesting/simulator.py

# CORRECT — homebrew python 3.13 has all deps
/opt/homebrew/opt/python@3.13/bin/python3.13 backtesting/simulator.py
```

Check which python has jsonpickle: `python3 -c "import jsonpickle; print('ok')"`.
If that fails, find the right one with `which python3.13`.

### Git Required for Codex Review

`/codex:review` requires a git repository. If the project is not initialized:

```bash
git init && git add -A && git commit -m "feat: initial commit"
```

Then re-run the review.

## Platform Test Interpretation

**Critical**: The platform test covers only **1,000 iterations** (ts 0–99,900), which is the **first 10% of a full simulation day** (10,000 iterations, ts 0–999,900).

### Mapping test results to expected full-day PnL

| Test metric | Interpretation |
|-------------|----------------|
| "173973" in header | Run ID — NOT PnL |
| Graph endpoint (~8,900) | Actual PnL for the test window |
| PnL of 8,900 for 1,000 iter | Extrapolate: ×10 adjustment needed |

### Extrapolation formula (per product)

```
Full-day PnL estimate = test_pnl × (full_day_iters / test_iters)
                      × phase_adjustment_factor
```

For INTARIAN_PEPPER_ROOT (trend rider):
- Test window (ts 0–99,900) = entirely Phase 1 (buy phase)
- Full day includes Phase 2 (hold/drift) and Phase 3 (sell)
- Phase 3 contributes ~0 incremental PnL (just liquidates accumulated gains)
- Safe extrapolation: `test_pepper_pnl × 10 × 0.85` (discount for Phase 3 non-linearity)

### Simulator accuracy gap

Our local simulator is **conservative**: it only counts immediate fills (market orders crossing the book). The actual platform ALSO fills passive quotes when bots trade against them. Expect actual PnL to be **~30% higher** than local simulator output.

```
Actual platform PnL ≈ local_simulator_pnl × 1.3
```

This is expected — not a discrepancy to debug.

---

## Git Workflow

### Branch Strategy

- `main` — stable only. **Never commit directly to main.** All changes via PR.
- Working branch format: `round{N}/sena-{description}`

```bash
# Start new work
git checkout main && git pull origin main
git checkout -b round2/sena-osmium-tuning

# Auto-commit+push fires automatically after every file edit (hook)
# Manual commit with descriptive message before opening PR:
git add -A && git commit -m "feat: tighten osmium spread to ±3"
git push origin round2/sena-osmium-tuning
```

### PR Process

1. Work on branch until strategy is stable and backtested
2. Push is automatic via hook — branch already exists on GitHub
3. Signal Sena to review: "Ready for PR: `round2/sena-osmium-tuning`"
4. **Sena reviews and merges manually on GitHub** — never auto-merge
5. After merge: `git checkout main && git pull origin main`

### Rules

- **Never** edit files directly on `main`
- Auto-commit message format: `auto: HH:MM` — fine for WIP
- Write a descriptive commit message before final PR (`feat:`, `fix:`, `perf:`)
- One branch per feature/experiment — keep PRs small and focused
- Branch is deleted after merge; start fresh for the next experiment

### Hook Setup (local — not committed to repo)

The auto-commit+push hook lives in `.claude/settings.local.json` (gitignored).
Each Claude Code instance must set it up once:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "cd /Users/User/Documents/IMC_contest && BRANCH=$(git branch --show-current); if [ \"$BRANCH\" != \"main\" ] && [ -n \"$(git status --porcelain)\" ]; then git add -A && git commit -m \"auto: $(date '+%H:%M')\" && git push origin \"$BRANCH\"; fi",
        "description": "Auto-commit and push after every file edit (non-main branches only)"
      }
    ]
  }
}
```

---

## Platform Export Files

After each platform test run, download 3 files from the dashboard and store in `artifacts/round{N}/dashboard_exports/`.

### File Types

| File | Contents |
|------|---------|
| `round{N}_log_{id}.log` | Output of all `print()` statements in your code |
| `round{N}_result_{id}.json` | Full market data + per-product P&L + final positions |
| `round{N}_submission_{id}.py` | Exact Python code that ran on the platform |

### JSON Structure (`round{N}_result_{id}.json`)

| Field | Contents |
|-------|---------|
| `profit` | Total PnL for this run |
| `activitiesLog` | CSV: bid/ask/volume/mid_price/profit_and_loss per product per timestamp |
| `graphLog` | CSV: `timestamp;value` — cumulative PnL over time |
| `positions` | Final positions per symbol (includes XIRECS balance) |

### Analysis Snippets

```python
import json, csv, io

d = json.load(open("artifacts/round1/dashboard_exports/round1_result_XXXXX.json"))

# Total PnL
print(f"Total PnL: {d['profit']}")

# Final positions
print(f"Final positions: {d['positions']}")

# Per-product final P&L (last row per product in activitiesLog)
rows = list(csv.DictReader(io.StringIO(d['activitiesLog']), delimiter=';'))
for product in sorted(set(r['product'] for r in rows)):
    last = [r for r in rows if r['product'] == product][-1]
    print(f"  {product}: {last['profit_and_loss']}")
```

```bash
# Check log output (your print() statements)
cat artifacts/round1/dashboard_exports/round1_log_XXXXX.log
```

### Post-Run Workflow

After every platform submission:
1. Run the platform test
2. Download all 3 files → save to `artifacts/round{N}/dashboard_exports/`
3. Run the analysis snippets above for per-product breakdown
4. Cross-check: does per-product PnL match your local backtest?
5. Update `LESSONS.md` with any new findings
