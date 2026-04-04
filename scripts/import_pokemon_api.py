import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.db import get_engine
from lib.import_pokemon import upsert_sets, upsert_cards
from lib.pokemon_api import fetch_sets, fetch_cards_page


def main():
    parser = argparse.ArgumentParser(description="Import Pokemon TCG data into MySQL.")
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = no limit")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--query", type=str, default="", help="Pokemon TCG API query string, e.g. \"set.id:base1\"")
    parser.add_argument("--set-id", type=str, default="", help="Comma separated set IDs (overrides --query)")
    args = parser.parse_args()

    engine = get_engine()

    sets = fetch_sets()
    upsert_sets(engine, sets)
    print(f"Imported {len(sets)} sets.")

    query = args.query.strip()
    if args.set_id:
        parts = [p.strip() for p in args.set_id.split(",") if p.strip()]
        if parts:
            query = " OR ".join([f"set.id:{p}" for p in parts])

    page = args.start_page
    total_cards = 0
    while True:
        if args.max_pages and page >= args.start_page + args.max_pages:
            break
        data = fetch_cards_page(page, args.page_size, query=query or None)
        cards = data.get("data", [])
        if page == args.start_page:
            total_count = data.get("totalCount")
            if total_count is not None:
                print(f"API totalCount for query: {total_count}")
        if not cards:
            break
        count = upsert_cards(engine, cards)
        total_cards += count
        print(f"Page {page}: {count} cards (total {total_cards})")
        page += 1
        time.sleep(args.sleep)

    print(f"Done. Imported {total_cards} cards.")


if __name__ == "__main__":
    main()
