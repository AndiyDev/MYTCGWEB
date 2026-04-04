import uuid
from passlib.context import CryptContext
from sqlalchemy import text
import streamlit as st

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def get_current_user():
    return st.session_state.get("user")


def login_user(engine, username: str, password: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash, display_name, avatar_url, reputation_level FROM users WHERE username=:u"),
            {"u": username},
        ).mappings().first()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    user = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "avatar_url": row["avatar_url"],
        "reputation_level": row["reputation_level"],
    }
    st.session_state["user"] = user
    return user


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
            text("INSERT INTO users (id, username, password_hash, display_name) VALUES (:id, :u, :p, :d)"),
            {"id": user_id, "u": username, "p": hash_password(password), "d": display_name},
        )
    return user_id


def logout_user():
    st.session_state.pop("user", None)
