import os
try:
    import streamlit as st
except Exception:  # pragma: no cover - used in CLI context
    st = None
from sqlalchemy import create_engine


def _build_mysql_url():
    cfg = {}
    if st is not None:
        try:
            cfg = st.secrets.get("db", {})
        except Exception:
            cfg = {}
    host = cfg.get("host", os.getenv("DB_HOST"))
    port = cfg.get("port", os.getenv("DB_PORT", "3306"))
    name = cfg.get("name", os.getenv("DB_NAME"))
    user = cfg.get("user", os.getenv("DB_USER"))
    password = cfg.get("password", os.getenv("DB_PASSWORD"))
    if not all([host, port, name, user, password]):
        raise RuntimeError("Database credentials missing. Set st.secrets['db'] or env vars.")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


@st.cache_resource(show_spinner=False)
def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        url = _build_mysql_url()
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
