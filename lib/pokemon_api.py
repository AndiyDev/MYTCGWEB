import os
import time
from typing import Any

import requests
import streamlit as st


BASE_URL = "https://api.pokemontcg.io/v2"


def _headers() -> dict[str, str]:
    key = None
    try:
        key = st.secrets.get("pokemontcg_api_key")
    except Exception:
        key = None
    key = key or os.getenv("POKEMONTCG_API_KEY")
    return {"X-Api-Key": key} if key else {}


def _request(path: str, params: dict[str, Any] | None = None, retries: int = 3) -> dict:
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        resp = requests.get(url, params=params, headers=_headers(), timeout=60)
        if resp.status_code == 429 and attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


def fetch_sets() -> list[dict]:
    data = _request("/sets")
    return data.get("data", [])


def fetch_cards_page(page: int, page_size: int = 250, query: str | None = None) -> dict:
    params: dict[str, Any] = {"page": page, "pageSize": page_size}
    if query:
        params["q"] = query
    return _request("/cards", params=params)
