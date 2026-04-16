"""
IMC Prosperity 4 — Round 1 Submission
======================================
Products:  ASH_COATED_OSMIUM  |  INTARIAN_PEPPER_ROOT
Strategies:
  ASH_COATED_OSMIUM    : Mean-reversion market maker around 10000 (std ≈ 5)
  INTARIAN_PEPPER_ROOT : Trend rider — buy early, hold, sell late.
                         Price drifts +1000/day deterministically.
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import jsonpickle

# ── Constants ─────────────────────────────────────────────────────────────────

POSITION_LIMITS: Dict[str, int] = {
    "ASH_COATED_OSMIUM": 80,
    "INTARIAN_PEPPER_ROOT": 80,
}

# Timestamps go 0 → 999900 (10,000 iterations × 100)
DAY_END = 999_900

# ASH_COATED_OSMIUM: stable mean ~10000, std ≈ 5, bot half-spread ≈ 8
OSMIUM_FAIR_VALUE = 10_000
OSMIUM_AGGRESS_BUY_MAX  = OSMIUM_FAIR_VALUE - 2   # buy any ask < 9998
OSMIUM_AGGRESS_SELL_MIN = OSMIUM_FAIR_VALUE + 2   # sell any bid > 10002
OSMIUM_BID = OSMIUM_FAIR_VALUE - 3                 # passive bid
OSMIUM_ASK = OSMIUM_FAIR_VALUE + 3                 # passive ask

# INTARIAN_PEPPER_ROOT: trends +1000/day, bot half-spread ≈ 7-9
# Phase thresholds (fraction of day)
PEPPER_BUY_UNTIL  = 0.15   # aggressively buy in first 15% of day
PEPPER_SELL_FROM  = 0.85   # aggressively sell in last 15% of day
PEPPER_EMA_ALPHA  = 0.08   # slow EMA — tracks trend, filters noise


# ── Trader class ──────────────────────────────────────────────────────────────

class Trader:

    def bid(self) -> int:
        """Round 2 auction bid — update after watching A.R.I.A. Uplink for Round 2."""
        return 15

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, state: TradingState):
        data = self._load_state(state.traderData)
        result: Dict[str, List[Order]] = {}

        for product, depth in state.order_depths.items():
            pos = state.position.get(product, 0)
            limit = POSITION_LIMITS.get(product, 20)

            if product == "ASH_COATED_OSMIUM":
                result[product] = self._trade_osmium(product, depth, pos, limit)

            elif product == "INTARIAN_PEPPER_ROOT":
                result[product] = self._trade_pepper(
                    product, depth, pos, limit, state.timestamp, data
                )

            else:
                result[product] = []

        trader_data = self._save_state(data)
        return result, 0, trader_data

    # ── ASH_COATED_OSMIUM ─────────────────────────────────────────────────────

    def _trade_osmium(
        self, product: str, depth: OrderDepth, pos: int, limit: int
    ) -> List[Order]:
        """
        Mean-reversion market maker around fair value 10000.
        Step 1: aggressively take clearly mispriced orders.
        Step 2: post passive quotes for the remaining capacity.
        Inventory skew keeps position near 0.
        """
        orders: List[Order] = []
        buy_cap = limit - pos
        sell_cap = limit + pos

        # ── Step 1: aggressive taker ──
        for ask in sorted(depth.sell_orders):
            if ask >= OSMIUM_AGGRESS_BUY_MAX or buy_cap <= 0:
                break
            qty = min(-depth.sell_orders[ask], buy_cap)
            orders.append(Order(product, ask, qty))
            buy_cap -= qty

        for bid in sorted(depth.buy_orders, reverse=True):
            if bid <= OSMIUM_AGGRESS_SELL_MIN or sell_cap <= 0:
                break
            qty = min(depth.buy_orders[bid], sell_cap)
            orders.append(Order(product, bid, -qty))
            sell_cap -= qty

        # ── Step 2: passive market-making with inventory skew ──
        # skew ∈ [-1,+1]; positive = long, negative = short
        skew = pos / limit if limit else 0
        adj = round(skew * 2)  # shift quotes to lean against current inventory

        bid_price = OSMIUM_BID - adj
        ask_price = OSMIUM_ASK - adj

        if buy_cap > 0:
            orders.append(Order(product, bid_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order(product, ask_price, -sell_cap))

        return orders

    # ── INTARIAN_PEPPER_ROOT ──────────────────────────────────────────────────

    def _trade_pepper(
        self,
        product: str,
        depth: OrderDepth,
        pos: int,
        limit: int,
        timestamp: int,
        data: dict,
    ) -> List[Order]:
        """
        Trend-riding strategy.
        Price rises +1000 per day (= +0.001 per ts unit).

        Phase 1 (ts < 15% of day): Aggressively BUY up to position limit.
        Phase 2 (15% – 85%):       Light market making; maintain long bias.
        Phase 3 (ts > 85% of day): Aggressively SELL entire position.
        """
        mid = self._mid_price(depth)
        if mid is None:
            return []

        # ── Update EMA ──
        if "pepper_ema" not in data:
            data["pepper_ema"] = float(mid)
        ema = PEPPER_EMA_ALPHA * mid + (1 - PEPPER_EMA_ALPHA) * data["pepper_ema"]
        data["pepper_ema"] = ema
        fv = ema

        orders: List[Order] = []
        buy_cap = limit - pos
        sell_cap = limit + pos
        phase = timestamp / DAY_END  # 0.0 → 1.0

        if phase < PEPPER_BUY_UNTIL:
            # ── Phase 1: Buy everything we can ──
            # Take ALL asks up to fv + 15 (well above mid to ensure fills)
            for ask in sorted(depth.sell_orders):
                if ask > fv + 15 or buy_cap <= 0:
                    break
                qty = min(-depth.sell_orders[ask], buy_cap)
                orders.append(Order(product, ask, qty))
                buy_cap -= qty

            # Post aggressive bid just below bot's typical ask (fv+8) to attract fills
            if buy_cap > 0:
                bid_price = int(fv + 7)  # just below bot ask — high chance of fill
                orders.append(Order(product, bid_price, buy_cap))

        elif phase > PEPPER_SELL_FROM:
            # ── Phase 3: Close long position only (never go short) ──
            close_qty = max(0, pos)  # only sell what we hold; don't short
            for bid in sorted(depth.buy_orders, reverse=True):
                if bid < fv - 15 or close_qty <= 0:
                    break
                qty = min(depth.buy_orders[bid], close_qty)
                orders.append(Order(product, bid, -qty))
                close_qty -= qty

            # Post aggressive ask at bot's typical bid level to guarantee fill
            if close_qty > 0:
                ask_price = int(fv - 8)   # = bot's typical bid → immediate fill
                orders.append(Order(product, ask_price, -close_qty))

        else:
            # ── Phase 2: Maintain long, do light market making ──
            # Primary goal: stay near max long (ride the trend)
            # Secondary goal: earn spread on oscillations

            # If not yet at target long (= 70% of limit), buy aggressively
            target_pos = int(limit * 0.7)
            if pos < target_pos:
                for ask in sorted(depth.sell_orders):
                    if ask > fv + 12 or buy_cap <= 0:
                        break
                    qty = min(-depth.sell_orders[ask], buy_cap)
                    orders.append(Order(product, ask, qty))
                    buy_cap -= qty

            # Light market making: post wide quotes to earn spread without
            # risking adverse selection on the trend
            # Only post SELL if we're already well long (avoid going short)
            if pos >= target_pos and sell_cap > 0:
                ask_price = int(fv + 12)  # wide ask — only fill on big up-moves
                qty = min(sell_cap, 10)   # small size to not flatten too much
                orders.append(Order(product, ask_price, -qty))

            # Always post bid to refill long position
            if buy_cap > 0:
                bid_price = int(fv - 8)
                orders.append(Order(product, bid_price, buy_cap))

        return orders

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mid_price(self, depth: OrderDepth) -> float | None:
        bids = depth.buy_orders
        asks = depth.sell_orders
        if bids and asks:
            return (max(bids) + min(asks)) / 2
        if bids:
            return float(max(bids))
        if asks:
            return float(min(asks))
        return None

    def _load_state(self, trader_data: str) -> dict:
        if not trader_data:
            return {}
        try:
            return jsonpickle.decode(trader_data)
        except Exception:
            return {}

    def _save_state(self, data: dict) -> str:
        try:
            encoded = jsonpickle.encode(data)
            return encoded if len(encoded) < 45_000 else "{}"
        except Exception:
            return "{}"