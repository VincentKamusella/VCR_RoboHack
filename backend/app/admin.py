"""Command-line access to the bot's internal data.

  python -m app.admin wishlist            # pizzas users asked for that are not on the menu
  python -m app.admin orders --limit 10   # latest matched orders (full recipe payload)
  python -m app.admin resolve "doner kebab" added   # mark a wish as added / rejected
"""
from __future__ import annotations

import argparse
import json

from .config import Settings
from .data.state_store import StateStore


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    wl = sub.add_parser("wishlist", help="list requested pizzas missing from the menu")
    wl.add_argument("--status", default="open", choices=["open", "added", "rejected", "all"])
    od = sub.add_parser("orders", help="list matched orders")
    od.add_argument("--limit", type=int, default=20)
    rs = sub.add_parser("resolve", help="change the status of a wish")
    rs.add_argument("normalized", help="the normalized name shown by the wishlist command")
    rs.add_argument("status", choices=["open", "added", "rejected"])
    args = parser.parse_args(argv)

    store = StateStore(Settings.from_env().state_db_path)
    if args.command == "wishlist":
        rows = store.missing_pizzas(None if args.status == "all" else args.status)
        if not rows:
            print("No wishes.")
        for row in rows:
            print(f"{row['request_count']:>3}x  {row['requested']!r:<30} key={row['normalized']!r}  "
                  f"last={row['last_requested_at']}  status={row['status']}")
    elif args.command == "orders":
        print(json.dumps(store.orders(args.limit), indent=2, ensure_ascii=False))
    elif args.command == "resolve":
        ok = store.set_missing_status(args.normalized, args.status)
        print("updated" if ok else "not found")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
