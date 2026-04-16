# SKILLS.md — IMC Prosperity 4 Trading Strategy Reference

This file is the authoritative reference for all trading strategies, algorithms, and patterns used in this project.
Read this before implementing any strategy. Update it as new approaches are validated.

---

## 0. Mental Model of the Exchange

- Each iteration: bots post their orders in the **order book** → our `run()` sees them → we send orders → matching happens → next iteration
- We are the **only** active algorithm (no interaction with other teams)
- Bots are deterministic per simulation seed but varied — they represent realistic market participants
- Our orders that don't match immediately become **passive quotes** — bots may or may not trade against them
- Unfilled quotes are **cancelled** at end of iteration — we start fresh each time

---

## 1. Fair Value Estimation

The foundation of all strategies. Everything else derives from knowing where the "true price" is.

### Method A: Order Book Mid-Price

```python
def mid_price(order_depth: OrderDepth) -> float:
    best_bid = max(order_depth.buy_orders.keys())
    best_ask = min(order_depth.sell_orders.keys())
    return (best_bid + best_ask) / 2
```

**Use when**: Price is relatively stable, spread is consistent.

### Method B: Volume-Weighted Mid (VWMP)

```python
def vwmp(order_depth: OrderDepth) -> float:
    bid_vol = sum(order_depth.buy_orders.values())
    ask_vol = sum(-v for v in order_depth.sell_orders.values())
    best_bid = max(order_depth.buy_orders.keys())
    best_ask = min(order_depth.sell_orders.keys())
    # Weight mid toward the thinner side (less supply/demand = price pressure)
    return (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)
```

**Use when**: Bid/ask volumes are asymmetric (order flow imbalance signal).

### Method C: Exponential Moving Average (EMA)

```python
# In state dict (persisted via traderData)
ema = alpha * new_mid + (1 - alpha) * prev_ema
# alpha = 0.1 → slow (stable), 0.3 → fast (reactive)
```

**Use when**: Product has trending price. EMA smooths noise.

### Method D: Historical Mean Reversion Anchor

If past data shows price oscillates around a stable value (e.g., RAINFOREST_RESIN = 10000),
hardcode or initialize the fair value and let EMA drift from it.

---

## 2. Market Making

**Strategy**: Quote both buy and sell around fair value. Earn the spread repeatedly.
**Best for**: Stable products with mean-reverting prices.

### Core Algorithm

```python
def market_make(
    product: str,
    fair_value: float,
    spread: int,           # half-spread (quote fair ± spread)
    state: TradingState,
    position_limit: int,
) -> list[Order]:
    pos = state.position.get(product, 0)
    orders = []

    # Skew quotes based on inventory to avoid position runaway
    skew = pos / position_limit  # in [-1, 1]
    bid_price = round(fair_value - spread - skew * spread)
    ask_price = round(fair_value + spread - skew * spread)

    # Buy up to limit
    remaining_buy = position_limit - pos
    if remaining_buy > 0:
        orders.append(Order(product, bid_price, remaining_buy))

    # Sell down to -limit
    remaining_sell = position_limit + pos
    if remaining_sell > 0:
        orders.append(Order(product, ask_price, -remaining_sell))

    return orders
```

### Inventory Skew

When long (pos > 0): lower both bid and ask → less eager to buy, more eager to sell.
When short (pos < 0): raise both → more eager to buy, less to sell.
This naturally mean-reverts the position without explicit unwinding logic.

### Aggressing Mispriced Orders

Don't only post passive quotes. If a bot offers a price clearly below fair value, **take it immediately**:

```python
for ask_price, ask_vol in sorted(order_depth.sell_orders.items()):
    if ask_price < fair_value - 1:  # clearly cheap
        qty = min(-ask_vol, remaining_buy)
        orders.append(Order(product, ask_price, qty))
        remaining_buy -= qty
```

---

## 3. Mean Reversion

**Strategy**: When price deviates significantly from a rolling mean, bet on reversion.
**Best for**: Products with oscillating prices (no persistent trend).

```python
def mean_reversion_signal(
    mid: float,
    rolling_mean: float,
    rolling_std: float,
    z_threshold: float = 1.5,
) -> int:
    """Returns +1 (buy), -1 (sell), 0 (no signal)"""
    if rolling_std == 0:
        return 0
    z = (mid - rolling_mean) / rolling_std
    if z < -z_threshold:
        return 1   # price below mean → buy
    if z > z_threshold:
        return -1  # price above mean → sell
    return 0
```

### Rolling Stats (Online, No Pandas)

```python
# Welford's online algorithm — O(1) per update, no history buffer needed
class OnlineStats:
    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0

    def update(self, x: float):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.M2 += delta * (x - self.mean)

    @property
    def std(self) -> float:
        return (self.M2 / self.n) ** 0.5 if self.n > 1 else 0.0
```

**Important**: Serialize this to `traderData` between iterations.

---

## 4. Trend Following / Momentum

**Strategy**: When price is trending, ride the momentum.
**Best for**: Products with persistent directional moves.

```python
def momentum_signal(prices: list[float], short_window: int = 5, long_window: int = 20) -> int:
    """Returns +1 (uptrend), -1 (downtrend), 0 (no signal)"""
    if len(prices) < long_window:
        return 0
    short_ema = prices[-short_window:]
    long_ema = prices[-long_window:]
    short_mean = sum(short_ema) / len(short_ema)
    long_mean = sum(long_ema) / len(long_ema)
    if short_mean > long_mean * 1.001:
        return 1
    if short_mean < long_mean * 0.999:
        return -1
    return 0
```

**Warning**: Trend following can lose badly in mean-reverting markets. Only use if data confirms trend behavior.

---

## 5. Cross-Product Arbitrage

**Strategy**: When two products are correlated, trade the spread between them.
**Best for**: When a new product is introduced that is economically linked to an existing one (e.g., raw material vs. processed good).

```python
def spread_signal(price_a: float, price_b: float, ratio: float, threshold: float) -> int:
    """ratio = expected price_a / price_b"""
    spread = price_a - ratio * price_b
    if spread < -threshold:
        return 1   # buy A, sell B
    if spread > threshold:
        return -1  # sell A, buy B
    return 0
```

**Caution**: Requires understanding the fundamental relationship. Never assume correlation without evidence from the data.

---

## 6. Conversion Requests

Used for products with a secondary market (e.g., goods that can be "converted" from one form to another at a cost).

```python
# After acquiring position via trading, convert to exit at a profit
# Net PnL = conversion_price - (transport_fees + import_tariff)
def should_convert(obs: ConversionObservation, position: int) -> int:
    if position > 0:
        # We're long — can we profitably sell via conversion?
        net_sell = obs.bidPrice - obs.transportFees - obs.exportTariff
        if net_sell > 0:  # profitable to convert
            return -position  # convert all
    return 0
```

---

## 7. Position Management Rules

**Never breach position limits** — all orders get silently cancelled.

```python
def clamp_to_limit(orders: list[Order], pos: int, limit: int) -> list[Order]:
    safe = []
    buy_remaining = limit - pos
    sell_remaining = limit + pos
    for o in orders:
        if o.quantity > 0:
            qty = min(o.quantity, buy_remaining)
            if qty > 0:
                safe.append(Order(o.symbol, o.price, qty))
                buy_remaining -= qty
        else:
            qty = max(o.quantity, -sell_remaining)
            if qty < 0:
                safe.append(Order(o.symbol, o.price, qty))
                sell_remaining += qty
    return safe
```

**Inventory target**: Aim for position near 0 at end of simulation to avoid unwind risk.

---

## 8. State Serialization Pattern

```python
import jsonpickle

# At START of run()
def _load_state(self, trader_data: str) -> dict:
    if not trader_data:
        return {}
    try:
        return jsonpickle.decode(trader_data)
    except Exception:
        return {}

# At END of run(), return as 3rd element
def _save_state(self, state_dict: dict) -> str:
    encoded = jsonpickle.encode(state_dict)
    # Guard against size limit
    if len(encoded) > 45_000:
        # Drop oldest history entries
        for key in state_dict:
            if isinstance(state_dict[key], list):
                state_dict[key] = state_dict[key][-50:]
        encoded = jsonpickle.encode(state_dict)
    return encoded
```

---

## 9. Backtesting Checklist

Before submitting, validate locally:
- [ ] Total PnL is positive across all products
- [ ] No position limit breaches (check logs for "ORDER REJECTED")
- [ ] `traderData` size stays < 45k chars (leave buffer for the 50k limit)
- [ ] `run()` executes in < 100ms average (time 100 iterations locally)
- [ ] Strategy logic handles empty order books gracefully (bots may not always post)

---

## 10. Round-by-Round Strategy Calibration

Each round introduces new products. Recalibrate per product:

| Signal | Tool | When to use |
|--------|------|-------------|
| Price stable, spread exists | Market Making | Most products |
| Price oscillates around a level | Mean Reversion | Check autocorrelation |
| Price trends persistently | Momentum | Check slope of prices |
| Two prices move together | Spread Arbitrage | Check correlation |
| Conversion available | Conversion Arb | Check net-of-fees profit |

**Data-driven calibration process:**
1. Download CSV data from dashboard (Data Capsule)
2. Plot price series: identify stable / oscillating / trending behavior
3. Compute optimal spread: ~30-50% of realized volatility
4. Compute optimal EMA alpha: minimize prediction error on historical data
5. Run backtest → verify positive PnL before submitting

---

## 11. Round 1 Products — Confirmed Analysis

| Product | Symbol | Limit | Fair Value | Strategy | Key Finding |
|---------|--------|-------|------------|----------|-------------|
| Ash-Coated Osmium | `ASH_COATED_OSMIUM` | ±80 | ~10000 (stable, std≈5) | Mean-reversion MM | Bot half-spread ≈ 8. Quote ±3. Aggress < 9998 / > 10002 |
| Intarian Pepper Root | `INTARIAN_PEPPER_ROOT` | ±80 | Trends +1000/day | Trend riding | +1000/day = +0.001/ts-unit. Buy early, hold, sell late. Bot half-spread ≈ 8. |

### INTARIAN_PEPPER_ROOT Deep Analysis

- **Trend**: Exactly +1000 per day (verified across 3 days: D-2=10k→11k, D-1=11k→12k, D0=12k→13k)
- **Rate**: +1000 / 999900 ts ≈ **0.001 per timestamp unit** (= 1.0 per 1000 ts = 100 per 100k ts)
- **Within-day std**: 288.7 (price oscillates ±288 around the trend line)
- **Bot bid-ask spread**: ~15 wide (half-spread ≈ 7.5)
- **Backtest PnL per day**: ~66,800 XIREC (conservative — passive fills not counted)
- **Theoretical max per day**: 80 units × (1000 - 16) ≈ 78,720 XIREC
- **Phase thresholds**: Buy in first 15% (ts < 150k), Hold in middle 70%, Sell in last 15% (ts > 850k)

### ASH_COATED_OSMIUM Deep Analysis

- **Fair value**: 10000 ± 5.5 std across all 3 days (essentially constant)
- **Bot bid-ask spread**: ~16 wide (half-spread ≈ 8)
- **Our quotes**: bid=9997, ask=10003 (INSIDE bot spread → passive fills from bots)
- **Backtest PnL per day**: ~5,000 XIREC (conservative — passive fills account for most real profit)
- **Risk**: Hits position limit ±80 sometimes. Skew adjustment mitigates but doesn't eliminate.

### Conservative Backtest Summary (3 days)

| Day | PEPPER | OSMIUM | Total |
|-----|--------|--------|-------|
| -2  | 66,882 | 4,713  | 71,595 |
| -1  | 66,797 | 6,276  | 73,073 |
|  0  | 66,813 | 5,170  | 71,983 |
| **Total** | **200,492** | **16,159** | **216,651** |

### Platform Test Result (1,000 iterations, ts 0–99,900)

| Product | Test PnL | Notes |
|---------|----------|-------|
| INTARIAN_PEPPER_ROOT | ~7,352 | Phase 1 only (buying phase); extrapolates to ~73,520/day |
| ASH_COATED_OSMIUM | ~1,548 | Consistent; extrapolates to ~15,480/day |
| **Total test PnL** | **~8,900** | Graph endpoint value |
| **Extrapolated full day** | **~89,000–99,400** | With Phase 2/3 adjustment |

### Round 1 Improvements Queue

Identified improvements not yet implemented (backtest first before deploying):

1. **OSMIUM spread tightening**: Try `OSMIUM_BID = 9998`, `OSMIUM_ASK = 10002` (±2 instead of ±3).
   - Tighter spread → more passive fills from bots → higher PnL
   - Risk: adverse selection if fair value drifts (std is only 5, so manageable)

2. **Phase 1 bid aggression**: Change `bid_price = int(fv + 7)` to `int(fv + 8)` or `int(fv + 9)`.
   - Bot typical ask = fv + 8; bidding at fv+8 matches it exactly → guaranteed fill
   - Current fv+7 misses fills by 1 tick

3. **Phase 2 dead code removal**: The sell order `ask_price = int(fv + 12), qty = min(sell_cap, 10)` 
   almost never fires in practice (we maintain pos ≥ 56 = 70% of 80).
   Replace with: if pos < target, buy more aggressively (fv + 10 instead of fv + 12).
