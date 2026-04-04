import uuid
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

        listing_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO listings (id, item_id, seller_id, price, currency, notes, status)
                VALUES (:id, :item, :seller, :price, :currency, :notes, 'ACTIVE')
                """
            ),
            {"id": listing_id, "item": item_id, "seller": seller_id, "price": price, "currency": currency, "notes": notes},
        )
        conn.execute(
            text("UPDATE card_instances SET locked_by_listing_id = :lid WHERE id=:id"),
            {"id": item_id, "lid": listing_id},
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


def create_interest(engine, listing_id: str, buyer_id: str):
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id FROM interests WHERE listing_id=:l AND buyer_id=:b"),
            {"l": listing_id, "b": buyer_id},
        ).first()
        if exists:
            return
        conn.execute(
            text("INSERT INTO interests (id, listing_id, buyer_id, status) VALUES (UUID(), :l, :b, 'PENDING')"),
            {"l": listing_id, "b": buyer_id},
        )


def list_interests_for_seller(engine, seller_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT i.id, i.status, u.username AS buyer, l.id AS listing_id,
                       c.name, c.card_number, c.image_url
                FROM interests i
                JOIN listings l ON l.id = i.listing_id
                JOIN users u ON u.id = i.buyer_id
                JOIN card_instances ci ON ci.id = l.item_id
                JOIN tcg_cards c ON c.id = ci.card_id
                WHERE l.seller_id=:s
                ORDER BY i.created_at DESC
                """
            ),
            {"s": seller_id},
        ).mappings().all()
    return rows


def update_interest(engine, interest_id: str, seller_id: str, status: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT i.id, l.seller_id, l.item_id, i.buyer_id
                FROM interests i JOIN listings l ON l.id = i.listing_id
                WHERE i.id=:id
                """
            ),
            {"id": interest_id},
        ).mappings().first()
        if not row or row["seller_id"] != seller_id:
            return None

        conn.execute(text("UPDATE interests SET status=:s WHERE id=:id"), {"s": status, "id": interest_id})
        if status == "ACCEPTED":
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (id, buyer_id, seller_id, item_id, status)
                    VALUES (UUID(), :b, :s, :item, 'PENDING')
                    """
                ),
                {"b": row["buyer_id"], "s": seller_id, "item": row["item_id"]},
            )
    return status


def list_transactions(engine, user_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT t.id, t.status, u.username AS buyer, u2.username AS seller,
                       c.name, c.card_number, c.image_url
                FROM transactions t
                JOIN users u ON u.id = t.buyer_id
                JOIN users u2 ON u2.id = t.seller_id
                JOIN card_instances ci ON ci.id = t.item_id
                JOIN tcg_cards c ON c.id = ci.card_id
                WHERE t.buyer_id=:u OR t.seller_id=:u
                ORDER BY t.created_at DESC
                """
            ),
            {"u": user_id},
        ).mappings().all()
    return rows


def update_transaction(engine, tx_id: str, user_id: str, status: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT buyer_id, seller_id, item_id FROM transactions WHERE id=:id"),
            {"id": tx_id},
        ).mappings().first()
        if not row or (row["buyer_id"] != user_id and row["seller_id"] != user_id):
            return False
        conn.execute(text("UPDATE transactions SET status=:s WHERE id=:id"), {"s": status, "id": tx_id})
        if status == "COMPLETED":
            conn.execute(text("UPDATE card_instances SET owner_id=:b, locked_by_listing_id=NULL WHERE id=:item"), {"b": row["buyer_id"], "item": row["item_id"]})
            conn.execute(text("UPDATE listings SET status='SOLD' WHERE item_id=:item"), {"item": row["item_id"]})
    return True
