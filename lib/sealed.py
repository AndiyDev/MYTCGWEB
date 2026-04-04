import uuid
from datetime import date

from sqlalchemy import text


def list_sealed_products(engine, game: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, game, type, set_id, name, image_url, cards_per_pack, msrp
                FROM sealed_products WHERE game=:g ORDER BY name
                """
            ),
            {"g": game},
        ).mappings().all()
    return rows


def create_sealed_product(engine, pid: str, game: str, type_label: str, set_id: str | None,
                          name: str, image_url: str | None, cards_per_pack: int, msrp: float | None):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO sealed_products (id, game, type, set_id, name, image_url, cards_per_pack, msrp)
                VALUES (:id, :g, :t, :sid, :n, :img, :cpp, :msrp)
                ON DUPLICATE KEY UPDATE
                    set_id=VALUES(set_id),
                    name=VALUES(name),
                    image_url=VALUES(image_url),
                    cards_per_pack=VALUES(cards_per_pack),
                    msrp=VALUES(msrp),
                    type=VALUES(type)
                """
            ),
            {
                "id": pid,
                "g": game,
                "t": type_label,
                "sid": set_id,
                "n": name,
                "img": image_url,
                "cpp": cards_per_pack,
                "msrp": msrp,
            },
        )


def add_sealed_instance(engine, owner_id: str, sealed_product_id: str, purchase_price: float, purchase_date: date | None, notes: str | None = None):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO sealed_instances (id, owner_id, sealed_product_id, purchase_price, purchase_date, notes)
                VALUES (UUID(), :uid, :pid, :price, :pdate, :notes)
                """
            ),
            {
                "uid": owner_id,
                "pid": sealed_product_id,
                "price": purchase_price,
                "pdate": purchase_date,
                "notes": notes,
            },
        )


def list_user_sealed(engine, owner_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT si.id, si.purchase_price, si.purchase_date, si.state, si.opened_at, si.notes,
                       sp.name, sp.type, sp.set_id, sp.cards_per_pack, sp.image_url
                FROM sealed_instances si
                JOIN sealed_products sp ON sp.id = si.sealed_product_id
                WHERE si.owner_id=:uid
                ORDER BY si.created_at DESC
                """
            ),
            {"uid": owner_id},
        ).mappings().all()
    return rows


def open_booster(engine, owner_id: str, sealed_instance_id: str, card_numbers: list[str], variants: list[str] | None = None):
    variants = variants or []
    with engine.begin() as conn:
        si = conn.execute(
            text(
                """
                SELECT si.id, si.purchase_price, si.state, sp.set_id, sp.cards_per_pack
                FROM sealed_instances si
                JOIN sealed_products sp ON sp.id = si.sealed_product_id
                WHERE si.id=:id AND si.owner_id=:uid
                """
            ),
            {"id": sealed_instance_id, "uid": owner_id},
        ).mappings().first()
        if not si or si["state"] != "SEALED":
            return "not_available", None
        set_id = si["set_id"]
        if not set_id:
            return "missing_set", None
        cards_per_pack = int(si["cards_per_pack"] or 10)
        if len(card_numbers) != cards_per_pack:
            return "count_mismatch", None

        opening_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO booster_openings (id, owner_id, sealed_instance_id, set_id, total_spent)
                VALUES (:id, :uid, :sid, :set_id, :spent)
                """
            ),
            {
                "id": opening_id,
                "uid": owner_id,
                "sid": sealed_instance_id,
                "set_id": set_id,
                "spent": float(si["purchase_price"] or 0),
            },
        )

        per_price = float(si["purchase_price"] or 0) / cards_per_pack if cards_per_pack else 0

        for idx, num in enumerate(card_numbers):
            num = num.strip()
            card = conn.execute(
                text(
                    """
                    SELECT id FROM tcg_cards
                    WHERE set_id=:sid AND card_number=:num
                    LIMIT 1
                    """
                ),
                {"sid": set_id, "num": num},
            ).mappings().first()
            if not card:
                return f"missing_card:{num}", None
            variant = variants[idx] if idx < len(variants) and variants[idx] else "Normal"
            conn.execute(
                text(
                    """
                    INSERT INTO card_instances (id, owner_id, card_id, variant, condition_label, purchase_price, purchase_date)
                    VALUES (UUID(), :uid, :cid, :v, 'Near Mint', :price, CURDATE())
                    """
                ),
                {"uid": owner_id, "cid": card["id"], "v": variant, "price": per_price},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO booster_opening_cards (id, opening_id, card_id, variant, market_value_snapshot)
                    VALUES (UUID(), :oid, :cid, :v, 0)
                    """
                ),
                {"oid": opening_id, "cid": card["id"], "v": variant},
            )

        conn.execute(
            text("UPDATE sealed_instances SET state='OPENED', opened_at=NOW() WHERE id=:id"),
            {"id": sealed_instance_id},
        )

    return "ok", opening_id


def list_openings(engine, owner_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT bo.id, bo.opened_at, bo.total_spent, bo.estimated_value, bo.net_value,
                       sp.name AS sealed_name, sp.set_id
                FROM booster_openings bo
                JOIN sealed_instances si ON si.id = bo.sealed_instance_id
                JOIN sealed_products sp ON sp.id = si.sealed_product_id
                WHERE bo.owner_id=:uid
                ORDER BY bo.opened_at DESC
                """
            ),
            {"uid": owner_id},
        ).mappings().all()
    return rows


def list_opening_cards(engine, opening_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT boc.card_id, boc.variant, c.name, c.card_number, c.image_url
                FROM booster_opening_cards boc
                JOIN tcg_cards c ON c.id = boc.card_id
                WHERE boc.opening_id=:oid
                ORDER BY CAST(c.card_number AS UNSIGNED)
                """
            ),
            {"oid": opening_id},
        ).mappings().all()
    return rows


def get_cards_by_numbers(engine, set_id: str, numbers: list[str]):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, name, card_number, image_url
                FROM tcg_cards
                WHERE set_id=:sid AND card_number IN :nums
                """
            ),
            {"sid": set_id, "nums": tuple(numbers)},
        ).mappings().all()
    return rows
