from sqlalchemy import text


def list_owned_cards(engine, user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT ci.id AS instance_id, ci.purchase_price, ci.purchase_date, ci.variant,
                       c.id AS card_id, c.name, c.card_number, c.rarity, s.set_name
                FROM card_instances ci
                JOIN tcg_cards c ON c.id = ci.card_id
                LEFT JOIN tcg_sets s ON s.id = c.set_id
                WHERE ci.owner_id=:uid
                ORDER BY ci.purchase_date DESC
                """
            ),
            {"uid": user_id},
        ).mappings().all()
    return rows
