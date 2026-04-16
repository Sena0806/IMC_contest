"""
Local backtesting simulator for IMC Prosperity 4.

Usage:
    python backtesting/simulator.py
    python backtesting/simulator.py --day 0
    python backtesting/simulator.py --day -1 --day -2

Reads:  backtesting/data/ROUND1/prices_round_1_day_{N}.csv
Output: Per-product PnL, total PnL, position history summary
"""

import sys
import csv
import argparse
import time
from pathlib import Path
from collections import defaultdict

# Allow importing from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datamodel import (
    OrderDepth, TradingState, Order, Trade, Listing, Observation
)
from trader import Trader, POSITION_LIMITS


# ── CSV loader ────────────────────────────────────────────────────────────────

def load_prices(filepath: Path) -> dict:
    """
    Returns: {timestamp: {product: OrderDepth}}
    """
    book: dict = defaultdict(dict)

    with open(filepath) as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ts = int(row["timestamp"])
            product = row["product"]
            depth = OrderDepth()

            for i in range(1, 4):
                bp_key = f"bid_price_{i}"
                bv_key = f"bid_volume_{i}"
                ap_key = f"ask_price_{i}"
                av_key = f"ask_volume_{i}"

                if row.get(bp_key) and row.get(bv_key):
                    try:
                        depth.buy_orders[int(float(row[bp_key]))] = int(row[bv_key])
                    except (ValueError, KeyError):
                        pass

                if row.get(ap_key) and row.get(av_key):
                    try:
                        # sell_orders have negative volume by convention
                        depth.sell_orders[int(float(row[ap_key]))] = -int(row[av_key])
                    except (ValueError, KeyError):
                        pass

            book[ts][product] = depth

    return book


# ── Exchange matching ─────────────────────────────────────────────────────────

def match_orders(
    orders: list[Order],
    depth: OrderDepth,
    position: int,
    limit: int,
) -> tuple[list[tuple[int, int]], int]:
    """
    Simulate immediate fills against the provided order book.
    Returns: (fills [(price, qty)], new_position)
    Conservative: only fills if our order crosses the existing book.
    Passive orders left in book are NOT filled (worst-case estimate).
    """
    fills = []
    pos = position

    buy_cap = limit - pos
    sell_cap = limit + pos

    for order in orders:
        qty = order.quantity  # positive=buy, negative=sell

        if qty > 0:  # BUY order
            # Fill against asks at or below our price
            for ask_price in sorted(depth.sell_orders.keys()):
                if ask_price > order.price:
                    break
                if buy_cap <= 0:
                    break
                available = -depth.sell_orders[ask_price]
                filled = min(qty, available, buy_cap)
                if filled > 0:
                    fills.append((ask_price, filled))
                    pos += filled
                    buy_cap -= filled
                    qty -= filled

        elif qty < 0:  # SELL order
            # Fill against bids at or above our price
            for bid_price in sorted(depth.buy_orders.keys(), reverse=True):
                if bid_price < order.price:
                    break
                if sell_cap <= 0:
                    break
                available = depth.buy_orders[bid_price]
                filled = min(-qty, available, sell_cap)
                if filled > 0:
                    fills.append((bid_price, -filled))
                    pos -= filled
                    sell_cap -= filled
                    qty += filled

    return fills, pos


# ── Main simulator ────────────────────────────────────────────────────────────

def run_simulation(price_file: Path, verbose: bool = False) -> dict:
    print(f"\n{'='*60}")
    print(f"  Simulating: {price_file.name}")
    print(f"{'='*60}")

    book = load_prices(price_file)
    trader = Trader()

    positions: dict[str, int] = defaultdict(int)
    cash: dict[str, float] = defaultdict(float)
    trader_data = ""

    timestamps = sorted(book.keys())
    products_seen = set()

    start_time = time.perf_counter()
    iteration_times = []

    for ts in timestamps:
        depths = book[ts]
        products_seen.update(depths.keys())

        listings = {p: Listing(p, p, "XIRECS") for p in depths}
        own_trades = {p: [] for p in depths}
        market_trades = {p: [] for p in depths}
        observations = Observation({}, {})

        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings=listings,
            order_depths=depths,
            own_trades=own_trades,
            market_trades=market_trades,
            position=dict(positions),
            observations=observations,
        )

        t0 = time.perf_counter()
        try:
            result, conversions, trader_data = trader.run(state)
        except Exception as e:
            print(f"  [ERROR] trader.run() raised at ts={ts}: {e}")
            continue
        iteration_times.append(time.perf_counter() - t0)

        # Apply orders
        for product, orders in result.items():
            if not orders:
                continue
            depth = depths.get(product, OrderDepth())
            limit = POSITION_LIMITS.get(product, 20)
            pos = positions[product]

            fills, new_pos = match_orders(orders, depth, pos, limit)

            for fill_price, fill_qty in fills:
                cash[product] -= fill_price * fill_qty  # cost of trade
                positions[product] += fill_qty

            if verbose and fills:
                print(f"  ts={ts:7d} {product}: fills={fills}  pos={positions[product]:+d}")

    elapsed = time.perf_counter() - start_time

    # ── Mark-to-market final PnL ──
    print(f"\n{'─'*60}")
    print(f"  {'Product':<30} {'Cash':>12}  {'Pos':>6}  {'MtM PnL':>12}")
    print(f"{'─'*60}")

    total_pnl = 0.0
    for product in sorted(products_seen):
        # Get last mid price
        last_mid = None
        for ts in reversed(timestamps):
            depth = book[ts].get(product)
            if depth:
                bids = depth.buy_orders
                asks = depth.sell_orders
                if bids and asks:
                    last_mid = (max(bids) + min(asks)) / 2
                    break
                elif bids:
                    last_mid = float(max(bids))
                    break
                elif asks:
                    last_mid = float(min(asks))
                    break

        if last_mid is None:
            last_mid = 0

        pos = positions[product]
        realized = cash[product]
        mtm = realized + pos * last_mid

        total_pnl += mtm
        print(f"  {product:<30} {realized:>12.1f}  {pos:>+6}  {mtm:>12.1f}")

    print(f"{'─'*60}")
    print(f"  {'TOTAL':<30} {'':>12}  {'':>6}  {total_pnl:>12.1f}")

    avg_iter_ms = (sum(iteration_times) / len(iteration_times) * 1000) if iteration_times else 0
    max_iter_ms = max(iteration_times) * 1000 if iteration_times else 0
    print(f"\n  Iterations : {len(timestamps)}")
    print(f"  Total time : {elapsed:.2f}s")
    print(f"  Avg iter   : {avg_iter_ms:.3f}ms  (limit: 900ms)")
    print(f"  Max iter   : {max_iter_ms:.3f}ms")
    print(f"  traderData : {len(trader_data)} chars  (limit: 50000)")

    if total_pnl > 0:
        print(f"\n  ✓ PnL POSITIVE — strategy profitable on this day")
    else:
        print(f"\n  ✗ PnL NEGATIVE — review strategy")

    return {
        "total_pnl": total_pnl,
        "positions": dict(positions),
        "cash": dict(cash),
        "avg_iter_ms": avg_iter_ms,
        "max_iter_ms": max_iter_ms,
        "trader_data_size": len(trader_data),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IMC Prosperity 4 Local Backtester")
    parser.add_argument("--day", type=str, action="append",
                        default=None, help="Day(s) to simulate: -2, -1, 0 (default: all)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print each fill")
    args = parser.parse_args()

    data_dir = Path(__file__).parent / "data" / "ROUND1"
    days = args.day or ["-2", "-1", "0"]

    results = []
    for day in days:
        fname = data_dir / f"prices_round_1_day_{day}.csv"
        if not fname.exists():
            print(f"[WARN] Not found: {fname}")
            continue
        r = run_simulation(fname, verbose=args.verbose)
        results.append(r)

    if len(results) > 1:
        grand_total = sum(r["total_pnl"] for r in results)
        print(f"\n{'='*60}")
        print(f"  GRAND TOTAL PnL ({len(results)} days): {grand_total:.1f}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
