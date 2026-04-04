import uuid
from sqlalchemy import text


def list_groups(engine):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT g.id, g.name, g.description,
                       (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) AS members
                FROM groups g
                ORDER BY g.name
                """
            )
        ).mappings().all()
    return rows


def create_group(engine, name: str, description: str | None):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO groups (id, name, description) VALUES (UUID(), :n, :d)"),
            {"n": name, "d": description},
        )


def join_group(engine, group_id: str, user_id: str):
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id FROM group_members WHERE group_id=:g AND user_id=:u"),
            {"g": group_id, "u": user_id},
        ).first()
        if exists:
            return
        conn.execute(
            text("INSERT INTO group_members (id, group_id, user_id, role) VALUES (UUID(), :g, :u, 'MEMBER')"),
            {"g": group_id, "u": user_id},
        )


def is_member(engine, group_id: str, user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM group_members WHERE group_id=:g AND user_id=:u"),
            {"g": group_id, "u": user_id},
        ).first()
    return row is not None


def list_posts(engine, group_id: str, category: str | None = None):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT gp.id, gp.category, gp.trade_type, gp.content, gp.status, gp.created_at,
                       u.username, u.display_name,
                       ci.id AS offered_item_id, c.name AS offered_name, c.card_number AS offered_number
                FROM group_posts gp
                JOIN users u ON u.id = gp.author_id
                LEFT JOIN card_instances ci ON ci.id = gp.offered_item_id
                LEFT JOIN tcg_cards c ON c.id = ci.card_id
                WHERE gp.group_id=:g
                """ + (" AND gp.category=:cat" if category else "") +
                " ORDER BY gp.created_at DESC"
            ),
            {"g": group_id, **({"cat": category} if category else {})},
        ).mappings().all()
    return rows


def create_post(engine, group_id: str, author_id: str, category: str, content: str, trade_type: str | None,
                offered_item_id: str | None, requested_card_id: str | None):
    with engine.begin() as conn:
        if category != "POST":
            row = conn.execute(
                text(
                    """
                    SELECT owner_id, state_label, locked_by_post_id, locked_by_listing_id
                    FROM card_instances WHERE id=:id
                    """
                ),
                {"id": offered_item_id},
            ).mappings().first()
            if not row or row["owner_id"] != author_id:
                return "not_owner"
            if row["state_label"] != "VERIFIED":
                return "not_verified"
            if row["locked_by_post_id"] or row["locked_by_listing_id"]:
                return "locked"

        post_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO group_posts (id, group_id, author_id, category, trade_type, offered_item_id, requested_card_id, content, status)
                VALUES (:id, :g, :a, :c, :t, :o, :r, :content, 'OPEN')
                """
            ),
            {
                "id": post_id,
                "g": group_id,
                "a": author_id,
                "c": category,
                "t": trade_type,
                "o": offered_item_id,
                "r": requested_card_id,
                "content": content,
            },
        )
        if offered_item_id:
            conn.execute(
                text("UPDATE card_instances SET locked_by_post_id = :pid WHERE id=:id"),
                {"id": offered_item_id, "pid": post_id},
            )
    return None


def delete_post(engine, post_id: str, user_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT author_id FROM group_posts WHERE id=:id"),
            {"id": post_id},
        ).mappings().first()
        if not row or row["author_id"] != user_id:
            return False
        conn.execute(
            text("UPDATE card_instances SET locked_by_post_id=NULL WHERE locked_by_post_id=:pid"),
            {"pid": post_id},
        )
        conn.execute(text("DELETE FROM group_posts WHERE id=:id"), {"id": post_id})
    return True
