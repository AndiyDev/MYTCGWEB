import argparse
import time

from lib.db import get_engine
from lib.import_pokemon import upsert_sets, upsert_cards
from lib.pokemon_api import fetch_sets, fetch_cards_page


def main():
    parser = argparse.ArgumentParser(description="Import Pokemon TCG data into MySQL.")
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = no limit")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    engine = get_engine()

    sets = fetch_sets()
    upsert_sets(engine, sets)
    print(f"Imported {len(sets)} sets.")

    page = args.start_page
    total_cards = 0
    while True:
        if args.max_pages and page >= args.start_page + args.max_pages:
            break
        data = fetch_cards_page(page, args.page_size)
        cards = data.get("data", [])
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
