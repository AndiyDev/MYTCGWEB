from sqlalchemy import text


def upsert_sets(engine, sets: list[dict]):
    if not sets:
        return 0
    with engine.begin() as conn:
        for s in sets:
            set_id = s.get("id")
            if not set_id:
                continue
            images = s.get("images") or {}
            total = s.get("total") or s.get("printedTotal") or 0
            conn.execute(
                text(
                    """
                    INSERT INTO tcg_sets (id, game, series, set_name, set_code, total_cards, logo_path, symbol_path)
                    VALUES (:id, 'pokemon', :series, :name, :code, :total, :logo, :symbol)
                    ON DUPLICATE KEY UPDATE
                        series=VALUES(series),
                        set_name=VALUES(set_name),
                        set_code=VALUES(set_code),
                        total_cards=VALUES(total_cards),
                        logo_path=VALUES(logo_path),
                        symbol_path=VALUES(symbol_path)
                    """
                ),
                {
                    "id": set_id,
                    "series": s.get("series"),
                    "name": s.get("name"),
                    "code": s.get("ptcgoCode"),
                    "total": int(total) if total else 0,
                    "logo": images.get("logo"),
                    "symbol": images.get("symbol"),
                },
            )
    return len(sets)


def upsert_cards(engine, cards: list[dict]):
    if not cards:
        return 0
    with engine.begin() as conn:
        for c in cards:
            card_id = c.get("id")
            set_info = c.get("set") or {}
            if not card_id or not set_info.get("id"):
                continue
            images = c.get("images") or {}
            tcgplayer = c.get("tcgplayer") or {}
            prices = tcgplayer.get("prices") or {}
            conn.execute(
                text(
                    """
                    INSERT INTO tcg_cards (id, set_id, card_number, name, rarity, image_url, has_normal, has_holofoil, has_reverse_holo)
                    VALUES (:id, :sid, :num, :name, :rar, :img, :hn, :hh, :hr)
                    ON DUPLICATE KEY UPDATE
                        set_id=VALUES(set_id),
                        card_number=VALUES(card_number),
                        name=VALUES(name),
                        rarity=VALUES(rarity),
                        image_url=VALUES(image_url),
                        has_normal=VALUES(has_normal),
                        has_holofoil=VALUES(has_holofoil),
                        has_reverse_holo=VALUES(has_reverse_holo)
                    """
                ),
                {
                    "id": card_id,
                    "sid": set_info.get("id"),
                    "num": c.get("number"),
                    "name": c.get("name"),
                    "rar": c.get("rarity"),
                    "img": images.get("large") or images.get("small"),
                    "hn": 1 if "normal" in prices else 1,
                    "hh": 1 if "holofoil" in prices else 0,
                    "hr": 1 if "reverseHolofoil" in prices else 0,
                },
            )
    return len(cards)
