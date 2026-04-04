import uuid
from datetime import timedelta
from passlib.context import CryptContext
from sqlalchemy import text
import streamlit as st

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def log_event(engine, user_id: str | None, action: str, meta: str | None = None):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO audit_logs (id, user_id, action, meta_json) VALUES (UUID(), :u, :a, :m)"),
            {"u": user_id, "a": action, "m": meta},
        )


def get_current_user():
    return st.session_state.get("user")


def login_user(engine, username: str, password: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, username, password_hash, display_name, avatar_url,
                       reputation_level, role, failed_login_attempts, locked_until
                FROM users WHERE username=:u
                """
            ),
            {"u": username},
        ).mappings().first()

        if not row:
            log_event(engine, None, "login_failed", f"user={username}")
            return None, "invalid"

        if row["locked_until"] and row["locked_until"] > conn.execute(text("SELECT NOW()")):
            log_event(engine, row["id"], "login_locked", None)
            return None, "locked"

        if not verify_password(password, row["password_hash"]):
            attempts = (row["failed_login_attempts"] or 0) + 1
            lock_until = None
            if attempts >= LOCKOUT_THRESHOLD:
                lock_until = conn.execute(text("SELECT DATE_ADD(NOW(), INTERVAL :m MINUTE)"), {"m": LOCKOUT_MINUTES}).scalar()
            conn.execute(
                text("UPDATE users SET failed_login_attempts=:a, locked_until=:l WHERE id=:id"),
                {"a": attempts, "l": lock_until, "id": row["id"]},
            )
            log_event(engine, row["id"], "login_failed", None)
            return None, "invalid"

        conn.execute(
            text("UPDATE users SET failed_login_attempts=0, locked_until=NULL, last_login_at=NOW() WHERE id=:id"),
            {"id": row["id"]},
        )

    user = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "avatar_url": row["avatar_url"],
        "reputation_level": row["reputation_level"],
        "role": row["role"] or "USER",
    }
    st.session_state["user"] = user
    log_event(engine, row["id"], "login_success", None)
    return user, None


def register_user(engine, username: str, password: str, display_name: str | None = None):
    user_id = str(uuid.uuid4())
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id FROM users WHERE username=:u"),
            {"u": username},
        ).first()
        if exists:
            return None
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role) "
                "VALUES (:id, :u, :p, :d, 'USER')"
            ),
            {"id": user_id, "u": username, "p": hash_password(password), "d": display_name},
        )
    log_event(engine, user_id, "register", None)
    return user_id


def require_admin(user: dict | None) -> bool:
    return bool(user and user.get("role") == "ADMIN")


def logout_user():
    st.session_state.pop("user", None)
