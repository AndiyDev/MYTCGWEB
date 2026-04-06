import re
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy import text
import streamlit as st

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,24}$")
MIN_PASSWORD_LEN = 8
SESSION_TTL_MINUTES = 120


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
    user = st.session_state.get("user")
    if not user:
        return None
    last_seen = st.session_state.get("last_seen_at")
    if last_seen and datetime.utcnow() - last_seen > timedelta(minutes=SESSION_TTL_MINUTES):
        st.session_state.pop("user", None)
        return None
    st.session_state["last_seen_at"] = datetime.utcnow()
    return user


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

        now_value = conn.execute(text("SELECT NOW()")).scalar()
        if row["locked_until"] and row["locked_until"] > now_value:
            log_event(engine, row["id"], "login_locked", None)
            return None, "locked"

        if not verify_password(password, row["password_hash"]):
            attempts = (row["failed_login_attempts"] or 0) + 1
            lock_until = None
            if attempts >= LOCKOUT_THRESHOLD:
                lock_until = conn.execute(
                    text("SELECT DATE_ADD(NOW(), INTERVAL :m MINUTE)"),
                    {"m": LOCKOUT_MINUTES},
                ).scalar()
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
    st.session_state["last_seen_at"] = datetime.utcnow()
    log_event(engine, row["id"], "login_success", None)
    return user, None


def validate_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.match(username or ""))


def validate_password(password: str) -> bool:
    return password is not None and len(password) >= MIN_PASSWORD_LEN


def register_user(engine, username: str, password: str, display_name: str | None = None):
    if not validate_username(username):
        return None, "invalid_username"
    if not validate_password(password):
        return None, "weak_password"

    user_id = str(uuid.uuid4())
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT id FROM users WHERE username=:u"),
            {"u": username},
        ).first()
        if exists:
            return None, "exists"
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, display_name, role) "
                "VALUES (:id, :u, :p, :d, 'USER')"
            ),
            {"id": user_id, "u": username, "p": hash_password(password), "d": display_name},
        )
    log_event(engine, user_id, "register", None)
    return user_id, None


def require_admin(user: dict | None) -> bool:
    return bool(user and user.get("role") == "ADMIN")


def logout_user():
    st.session_state.pop("user", None)
    st.session_state.pop("last_seen_at", None)
