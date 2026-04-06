from sqlalchemy import text


def get_sets(engine, game: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, set_name, series, total_cards, logo_path, symbol_path FROM tcg_sets WHERE game=:g ORDER BY set_name"),
            {"g": game},
        ).mappings().all()
    return rows


def get_db_counts(engine):
    with engine.begin() as conn:
        sets = conn.execute(text("SELECT COUNT(*) FROM tcg_sets")).scalar() or 0
        cards = conn.execute(text("SELECT COUNT(*) FROM tcg_cards")).scalar() or 0
    return int(sets), int(cards)


def get_set_progress(engine, user_id: str, game: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT s.id AS set_id, COUNT(DISTINCT c.id) AS owned
                FROM tcg_sets s
                LEFT JOIN tcg_cards c ON c.set_id = s.id
                LEFT JOIN card_instances ci ON ci.card_id = c.id AND ci.owner_id = :uid
                WHERE s.game = :g
                GROUP BY s.id
                """
            ),
            {"uid": user_id, "g": game},
        ).mappings().all()
    return {row["set_id"]: int(row["owned"] or 0) for row in rows}


def get_cards_for_set(engine, set_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, card_number, name, image_url, rarity,
                       has_normal, has_holofoil, has_reverse_holo
                FROM tcg_cards
                WHERE set_id=:sid
                ORDER BY CAST(card_number AS UNSIGNED)
                """
            ),
            {"sid": set_id},
        ).mappings().all()
    return rows


def get_user_variant_counts(engine, user_id: str, set_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id AS card_id, ci.variant, COUNT(*) as qty
                FROM card_instances ci
                JOIN tcg_cards c ON c.id = ci.card_id
                WHERE ci.owner_id=:uid AND c.set_id=:sid
                GROUP BY c.id, ci.variant
                """
            ),
            {"uid": user_id, "sid": set_id},
        ).mappings().all()
    counts = {}
    for row in rows:
        counts.setdefault(row["card_id"], {})[row["variant"]] = row["qty"]
    return counts


def add_instance(engine, user_id: str, card_id: str, variant: str, condition_label: str, purchase_price: float = 0.0):
    with engine.begin() as conn:
        flags = conn.execute(
            text(
                """
                SELECT has_normal, has_holofoil, has_reverse_holo
                FROM tcg_cards WHERE id=:cid
                """
            ),
            {"cid": card_id},
        ).mappings().first()
        if not flags:
            return False
        allowed = (
            (variant == "Normal" and flags["has_normal"]) or
            (variant == "Holofoil" and flags["has_holofoil"]) or
            (variant == "Reverse Holo" and flags["has_reverse_holo"])
        )
        if not allowed:
            return False

        conn.execute(
            text(
                """
                INSERT INTO card_instances (id, owner_id, card_id, variant, condition_label, purchase_price, purchase_date)
                VALUES (UUID(), :uid, :cid, :v, :c, :p, CURDATE())
                """
            ),
            {"uid": user_id, "cid": card_id, "v": variant, "c": condition_label, "p": purchase_price},
        )
    return True


def remove_instance(engine, user_id: str, card_id: str, variant: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM card_instances
                WHERE owner_id=:uid AND card_id=:cid AND variant=:v
                  AND locked_by_listing_id IS NULL AND locked_by_post_id IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": user_id, "cid": card_id, "v": variant},
        ).mappings().first()
        if not row:
            return False
        conn.execute(text("DELETE FROM card_instances WHERE id=:id"), {"id": row["id"]})
    return True


def update_purchase_price(engine, user_id: str, card_id: str, variant: str, price: float):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM card_instances
                WHERE owner_id=:uid AND card_id=:cid AND variant=:v
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": user_id, "cid": card_id, "v": variant},
        ).mappings().first()
        if not row:
            return False
        conn.execute(
            text("UPDATE card_instances SET purchase_price=:p WHERE id=:id"),
            {"p": price, "id": row["id"]},
        )
    return True
