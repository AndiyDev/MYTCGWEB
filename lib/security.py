import time
import streamlit as st


def rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    bucket = st.session_state.get(key, [])
    bucket = [t for t in bucket if now - t < window_seconds]
    if len(bucket) >= limit:
        st.session_state[key] = bucket
        return False
    bucket.append(now)
    st.session_state[key] = bucket
    return True


def clean_text(value: str, max_len: int = 500) -> str:
    if value is None:
        return ""
    value = value.strip()
    if len(value) > max_len:
        value = value[:max_len]
    return value
