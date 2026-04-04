from sqlalchemy import text


def list_listings(engine):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT l.id, l.price, l.currency, l.notes, l.status,
                       u.username AS seller,
                       c.name, c.card_number, c.image_url,
                       ci.id AS item_id
                FROM listings l
                JOIN users u ON u.id = l.seller_id
                JOIN card_instances ci ON ci.id = l.item_id
                JOIN tcg_cards c ON c.id = ci.card_id
                WHERE l.status IN ('ACTIVE','DRAFT')
                ORDER BY l.created_at DESC
                """
            )
        ).mappings().all()
    return rows


def create_listing(engine, seller_id: str, item_id: str, price: float, currency: str, notes: str | None):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT owner_id, state_label, locked_by_listing_id, locked_by_post_id
                FROM card_instances WHERE id=:id
                """
            ),
            {"id": item_id},
        ).mappings().first()
        if not row or row["owner_id"] != seller_id:
            return "not_owner"
        if row["state_label"] != "VERIFIED":
            return "not_verified"
        if row["locked_by_listing_id"] or row["locked_by_post_id"]:
            return "locked"

        conn.execute(
            text(
                """
                INSERT INTO listings (id, item_id, seller_id, price, currency, notes, status)
                VALUES (UUID(), :item, :seller, :price, :currency, :notes, 'ACTIVE')
                """
            ),
            {"item": item_id, "seller": seller_id, "price": price, "currency": currency, "notes": notes},
        )
        conn.execute(
            text("UPDATE card_instances SET locked_by_listing_id = LAST_INSERT_ID() WHERE id=:id"),
            {"id": item_id},
        )
    return None


def close_listing(engine, listing_id: str, seller_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT seller_id, item_id FROM listings WHERE id=:id"),
            {"id": listing_id},
        ).mappings().first()
        if not row or row["seller_id"] != seller_id:
            return False
        conn.execute(text("UPDATE listings SET status='ARCHIVED' WHERE id=:id"), {"id": listing_id})
        conn.execute(text("UPDATE card_instances SET locked_by_listing_id=NULL WHERE id=:iid"), {"iid": row["item_id"]})
    return True
