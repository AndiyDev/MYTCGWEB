from sqlalchemy import text


def get_user_by_username(engine, username: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, display_name FROM users WHERE username=:u"),
            {"u": username},
        ).mappings().first()
    return row


def get_room_items(engine, owner_id: str, public_only: bool = False):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT ri.id AS room_item_id, ri.slot_type, ri.furniture_id, ri.x_pos, ri.y_pos, ri.rotation,
                       ci.id AS item_id, ci.is_public, c.name, c.card_number, c.image_url
                FROM room_items ri
                JOIN card_instances ci ON ci.id = ri.item_id
                JOIN tcg_cards c ON c.id = ci.card_id
                WHERE ri.owner_id=:oid
                """ + (" AND ci.is_public=1" if public_only else "")
            ),
            {"oid": owner_id},
        ).mappings().all()
    return rows


def get_furniture(engine, owner_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, type, x_pos, y_pos, rotation
                FROM room_furniture
                WHERE owner_id=:oid
                ORDER BY created_at DESC
                """
            ),
            {"oid": owner_id},
        ).mappings().all()
    return rows


def add_furniture(engine, owner_id: str, type_label: str, x_pos: float, y_pos: float, rotation: float = 0.0):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO room_furniture (id, owner_id, type, x_pos, y_pos, rotation)
                VALUES (UUID(), :oid, :t, :x, :y, :r)
                """
            ),
            {"oid": owner_id, "t": type_label, "x": x_pos, "y": y_pos, "r": rotation},
        )


def remove_furniture(engine, owner_id: str, furniture_id: str):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM room_furniture WHERE id=:id AND owner_id=:oid"),
            {"id": furniture_id, "oid": owner_id},
        )


def get_available_items(engine, owner_id: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT ci.id AS item_id, c.name, c.card_number, c.image_url
                FROM card_instances ci
                JOIN tcg_cards c ON c.id = ci.card_id
                LEFT JOIN room_items ri ON ri.item_id = ci.id
                WHERE ci.owner_id=:oid AND ri.id IS NULL
                ORDER BY c.name
                """
            ),
            {"oid": owner_id},
        ).mappings().all()
    return rows


def place_item(engine, owner_id: str, item_id: str, slot_type: str, x_pos: float, y_pos: float, rotation: float = 0.0, furniture_id: str | None = None):
    with engine.begin() as conn:
        owner = conn.execute(
            text("SELECT owner_id FROM card_instances WHERE id=:id"),
            {"id": item_id},
        ).mappings().first()
        if not owner or owner["owner_id"] != owner_id:
            return False

        conn.execute(
            text(
                """
                DELETE FROM room_items
                WHERE owner_id=:oid AND slot_type=:s AND x_pos=:x AND y_pos=:y
                """
            ),
            {"oid": owner_id, "s": slot_type, "x": x_pos, "y": y_pos},
        )

        conn.execute(
            text(
                """
                INSERT INTO room_items (id, owner_id, item_id, slot_type, furniture_id, x_pos, y_pos, rotation)
                VALUES (UUID(), :oid, :iid, :s, :fid, :x, :y, :r)
                """
            ),
            {"oid": owner_id, "iid": item_id, "s": slot_type, "fid": furniture_id, "x": x_pos, "y": y_pos, "r": rotation},
        )
    return True


def clear_slot(engine, owner_id: str, slot_type: str, x_pos: float, y_pos: float):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM room_items
                WHERE owner_id=:oid AND slot_type=:s AND x_pos=:x AND y_pos=:y
                """
            ),
            {"oid": owner_id, "s": slot_type, "x": x_pos, "y": y_pos},
        )
