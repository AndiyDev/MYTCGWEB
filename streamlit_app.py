import os
import uuid
import streamlit as st
from sqlalchemy import text
from lib.db import get_engine
from lib.schema import init_schema
from lib.auth import login_user, register_user, logout_user, get_current_user, require_admin
from lib.collection import (
    get_sets,
    get_cards_for_set,
    get_user_variant_counts,
    add_instance,
    remove_instance,
    get_set_progress,
    update_purchase_price,
    get_db_counts,
)
from lib.pokemon_import import fetch_pokemon_card
from lib.pokemon_api import fetch_sets, fetch_cards_page
from lib.import_pokemon import upsert_sets, upsert_cards
from lib.pokemon_com import import_set_from_pokemon_com
from lib.pricing import scrape_source
from lib.analytics import list_owned_cards
from lib.sealed import (
    list_sealed_products,
    create_sealed_product,
    add_sealed_instance,
    list_user_sealed,
    open_booster,
    list_openings,
    list_opening_cards,
    get_cards_by_numbers,
)
from lib.sealed_scrape import scrape_featured_products
from lib.security import rate_limit, clean_text
from lib.room import (
    get_room_items,
    get_available_items,
    place_item,
    clear_slot,
    get_user_by_username,
    get_furniture,
    add_furniture,
    remove_furniture,
)
from lib.groups import list_groups, create_group, join_group, is_member, list_posts, create_post, delete_post
from lib.market import (
    list_listings,
    create_listing,
    close_listing,
    create_interest,
    list_interests_for_seller,
    update_interest,
    list_transactions,
    update_transaction,
)

st.set_page_config(page_title="MYTCGWEB", layout="wide", initial_sidebar_state="expanded")

engine = get_engine()


@st.cache_resource(show_spinner=False)
def ensure_schema():
    init_schema(engine)
    return True


ensure_schema()


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #0a0a0d;
  --panel: #13131a;
  --panel-2: #0f0f15;
  --panel-3: #0d0d12;
  --stroke: #20202b;
  --accent: #62f2d2;
  --accent-2: #3cc2ff;
  --accent-3: #ffb347;
  --text: #eef0f4;
  --muted: #9aa0ad;
  --glow: 0 16px 40px rgba(0,0,0,0.35);
}

html, body, [class*="css"]  { font-family: 'Space Grotesk', sans-serif; }
body {
  background:
    radial-gradient(900px 420px at 10% -10%, #1b1b28 0%, #0a0a0d 60%),
    radial-gradient(900px 480px at 110% 0%, #0b243c 0%, #0a0a0d 60%),
    radial-gradient(600px 260px at 50% 120%, #141421 0%, #0a0a0d 65%);
  color: var(--text);
}

section[data-testid="stSidebar"] {
  background: rgba(12, 12, 18, 0.95);
  border-right: 1px solid var(--stroke);
}
section[data-testid="stSidebar"] .stRadio > div { gap: 0.5rem; }
section[data-testid="stSidebar"] label { color: var(--text) !important; }
section[data-testid="stSidebar"] .stButton > button { width: 100%; }
section[data-testid="stSidebar"] .sidebar-card {
  background: linear-gradient(180deg, rgba(20,20,28,0.95), rgba(12,12,18,0.95));
  border: 1px solid #1f1f2b;
  padding: 14px;
  border-radius: 16px;
  box-shadow: var(--glow);
}
section[data-testid="stSidebar"] .sidebar-title {
  font-size: 0.75rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}
section[data-testid="stSidebar"] .sidebar-brand {
  font-weight: 700;
  font-size: 1.2rem;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
  background: linear-gradient(90deg, #ffffff, #7ef6da);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
section[data-testid="stSidebar"] .sidebar-user { display:flex; align-items:center; gap:12px; }
section[data-testid="stSidebar"] .avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: #161822;
  border: 1px solid #2a2c3a;
  display:flex;
  align-items:center;
  justify-content:center;
  color: #7ef6da;
  font-weight:700;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
  padding: 9px 10px;
  border-radius: 14px;
  background: #101018;
  border: 1px solid #1d1d2a;
  transition: all 0.2s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div { padding-left: 0; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label input { display: none; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label input:checked + div {
  background: linear-gradient(90deg, rgba(98,242,210,0.22), rgba(60,194,255,0.12));
  border-radius: 12px;
  padding: 8px 10px;
  border: 1px solid rgba(98,242,210,0.35);
  color: #ffffff;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
  border-color: rgba(98,242,210,0.4);
  transform: translateY(-1px);
}

div[data-testid="stVerticalBlock"] { gap: 1.2rem; }

.card { background: var(--panel); border: 1px solid var(--stroke); padding: 16px; border-radius: 16px; box-shadow: var(--glow); }
.section-title { font-size: 22px; font-weight: 700; margin: 10px 0; }

.stButton > button {
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: linear-gradient(180deg, #1a1a26 0%, #12121a 100%);
  color: var(--text);
  padding: 0.6rem 0.9rem;
}
.stButton > button:hover { border-color: #3a3a48; background: #1f1f2b; }
.stButton > button:focus { box-shadow: 0 0 0 2px rgba(109,242,215,0.25); }
button[kind="primary"] {
  background: linear-gradient(90deg, rgba(98,242,210,0.35), rgba(60,194,255,0.25));
  border: 1px solid rgba(98,242,210,0.4);
  color: #ffffff;
}
button[kind="primary"]:hover { border-color: rgba(98,242,210,0.6); }
input, textarea, select { border-radius: 10px !important; }
div[data-testid="stTextInput"] input {
  background: #0f1016;
  border: 1px solid #242433;
  color: var(--text);
  padding: 0.6rem 0.75rem;
  border-radius: 12px;
}
div[data-testid="stTextInput"] input:focus {
  border-color: rgba(98,242,210,0.6);
  box-shadow: 0 0 0 2px rgba(98,242,210,0.2);
}
div[data-testid="stSelectbox"] > div {
  background: #0f1016;
  border-radius: 12px;
  border: 1px solid #242433;
}

.muted { color: var(--muted); }

.collection-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.card-item {
  background: #0f1016;
  border: 1px solid #1c1c28;
  border-radius: 14px;
  padding: 10px;
  box-shadow: 0 10px 24px rgba(0,0,0,0.28);
  transition: transform 0.2s ease, border 0.2s ease, box-shadow 0.2s ease;
}
.card-item:hover { transform: translateY(-2px); border-color: rgba(98,242,210,0.25); box-shadow: 0 16px 30px rgba(0,0,0,0.35); }
.card-item .card-img {
  background: #0b0b10;
  border: 1px solid #1a1a26;
  border-radius: 12px;
  padding: 6px;
  margin-bottom: 8px;
}
.card-thumb { width: 100%; max-height: 170px; object-fit: contain; border-radius: 10px; }
.card-item .stButton > button {
  padding: 0.25rem 0.45rem;
  font-size: 0.78rem;
  border-radius: 8px;
  background: #141420;
  border: 1px solid #26263a;
  color: var(--text);
  min-width: 36px;
}
.card-item .name { font-weight: 600; font-size: 0.85rem; margin-bottom: 4px; }
.card-item .meta { color: var(--muted); font-size: 0.78rem; margin-top: 4px; }
.card-item .rarity { margin-top: 4px; }
.card-item .card-img img { width: 100%; height: auto; }
.badge { display: inline-block; padding: 4px 8px; border-radius: 999px; border: 1px solid var(--stroke); font-size: 0.75rem; color: var(--muted); }
.value { font-weight: 700; font-size: 1.15rem; }

.detail-card { background: #111118; border: 1px solid var(--stroke); border-radius: 18px; padding: 16px; }
.detail-title { font-size: 1.25rem; font-weight: 700; margin-top: 8px; }
.detail-sub { color: var(--muted); margin-top: 2px; }
.pill-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.detail-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.ghost-btn { border: 1px solid var(--stroke); padding: 8px 12px; border-radius: 999px; color: var(--text); background: #15151e; display: inline-block; }
.price-row { display: flex; justify-content: space-between; align-items: baseline; margin-top: 6px; }
.price { font-size: 1.4rem; font-weight: 700; color: #7ef6da; }
.price-sub { color: var(--muted); font-size: 0.85rem; }
.tabs { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-top: 12px; }
.tab { border: 1px solid var(--stroke); border-radius: 999px; padding: 8px; text-align: center; color: var(--muted); }
.tab.active { color: var(--text); background: #1a1a25; border-color: #2c2c3a; }
.chart { height: 180px; border-radius: 14px; border: 1px dashed #2b2b36; margin-top: 12px; position: relative; background: linear-gradient(180deg, rgba(110,242,215,0.08), rgba(0,0,0,0)); }
.chart-line { position: absolute; left: 12px; right: 12px; top: 40px; height: 2px; background: linear-gradient(90deg, rgba(110,242,215,0.6), rgba(110,242,215,0.1)); }
.slot-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.slot { border: 1px dashed #2b2b36; border-radius: 12px; padding: 8px; min-height: 140px; background: #0f0f16; }
.slot img { width: 100%; border-radius: 8px; }
.pack-row { display: flex; align-items: center; gap: 16px; margin: 8px 0 16px; }
.pack { width: 140px; height: 200px; border-radius: 14px; background: linear-gradient(160deg, #1c1c2b, #0f0f16); border: 1px solid #2b2b36; position: relative; overflow: hidden; }
.pack:after { content: ""; position: absolute; inset: 0; background: linear-gradient(130deg, rgba(109,242,215,0.25), rgba(0,0,0,0)); opacity: 0.7; }
.pack.opened { transform: rotate(-2deg); }
.pack-strip { position: absolute; left: 0; right: 0; top: 8px; height: 6px; background: rgba(255,255,255,0.08); }
.pack-title { font-size: 0.85rem; color: var(--muted); }
.animate-card { animation: flyout 0.6s ease forwards; }
@keyframes flyout { from { transform: translateY(-10px) scale(0.98); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }

.set-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.set-tile {
  background: linear-gradient(180deg, #13131b 0%, #0d0d14 100%);
  border: 1px solid #1f1f2d;
  border-radius: 18px;
  padding: 14px;
  box-shadow: var(--glow);
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 180px;
}
.set-media {
  background: #0b0b10;
  border: 1px solid #1f1f2d;
  border-radius: 14px;
  padding: 10px;
  min-height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.set-media img { max-height: 70px; width: 100%; object-fit: contain; }
.set-meta { display: flex; justify-content: space-between; align-items: center; }
.set-name { font-weight: 600; font-size: 0.95rem; }
.set-progress { color: var(--muted); font-size: 0.85rem; }

.set-hero {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid #1f1f2d;
  background: linear-gradient(120deg, rgba(18,18,26,0.95), rgba(10,10,15,0.95));
  box-shadow: var(--glow);
  margin-bottom: 12px;
}
.set-hero-logo {
  background: #0b0b10;
  border: 1px solid #1f1f2d;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  min-height: 110px;
}
.set-hero-logo img { max-width: 120px; max-height: 90px; object-fit: contain; }
.set-hero-title { font-size: 1.4rem; font-weight: 700; }
.set-hero-sub { color: var(--muted); margin-top: 4px; }
.set-hero-row { display: flex; gap: 10px; align-items: center; margin-top: 10px; }
.chip {
  border: 1px solid #262636;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.8rem;
  color: var(--muted);
  background: #101018;
}

.mobile-only { display: none; }
.top-bar { flex-direction: column; align-items: flex-start; }
.set-hero-logo { min-height: 90px; }
section[data-testid="stSidebar"] .sidebar-card { padding: 10px; }
.card-item { padding: 8px; }
.card-item .name { font-size: 0.85rem; }
.detail-title { font-size: 1.05rem; }
.tabs { grid-template-columns: 1fr 1fr 1fr; }
.set-tile { min-height: 160px; }
.set-hero { padding: 14px; }
.card { padding: 12px; }
.top-title { font-size: 1.3rem; }
section[data-testid="stSidebar"] { min-width: 240px; }

@media (min-width: 900px) {
  body { font-size: 1.05rem; }
  .card-item .name { font-size: 0.95rem; }
  .detail-title { font-size: 1.2rem; }
  .set-hero-title { font-size: 1.6rem; }
  .top-title { font-size: 1.6rem; }
}
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}
.top-title { font-size: 1.6rem; font-weight: 700; }
.top-sub { color: var(--muted); font-size: 0.9rem; }

.room-wrap { perspective: 900px; background: #0b0b10; padding: 20px; border-radius: 18px; border: 1px solid #1f1f2a; }
.room { position: relative; height: 360px; background: #0f1016; border-radius: 14px; overflow: hidden; }
.room-wall { position: absolute; background: #121621; border: 1px solid #1f1f2a; }
.wall-left { width: 40%; height: 100%; left: 0; transform: skewY(-2deg); }
.wall-right { width: 40%; height: 100%; right: 0; transform: skewY(2deg); }
.wall-back { width: 20%; height: 100%; left: 40%; background: #0e111a; }
.room-floor { position: absolute; bottom: 0; left: 0; right: 0; height: 35%; background: linear-gradient(180deg, #10131b, #0b0b10); }
.room-ceil { position: absolute; top: 0; left: 0; right: 0; height: 12%; background: #0c0c12; opacity: 0.8; }
.furniture { position: absolute; background: #1a1c26; border: 1px solid #2b2b36; border-radius: 8px; }
.furniture.shelf { width: 120px; height: 12px; }
.furniture.table { width: 140px; height: 18px; }
.furniture.stand { width: 50px; height: 50px; }
.room-card { position: absolute; width: 48px; }
.room-card img { width: 100%; border-radius: 6px; }
</style>
""",
    unsafe_allow_html=True,
)


def header():
    st.markdown("# MYTCGWEB")


def empty_state(text: str):
    st.markdown(f"<div class='card'>{text}</div>", unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner=False)
def cached_sets(game: str):
    return get_sets(engine, game)


@st.cache_data(ttl=30, show_spinner=False)
def cached_cards(set_id: str):
    return get_cards_for_set(engine, set_id)


@st.cache_data(ttl=20, show_spinner=False)
def cached_progress(user_id: str, game: str):
    return get_set_progress(engine, user_id, game)


@st.cache_data(ttl=20, show_spinner=False)
def cached_variant_counts(user_id: str, set_id: str):
    return get_user_variant_counts(engine, user_id, set_id)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_price(source: str, query: str):
    return scrape_source(source, query)


def login_view():
    st.markdown("## Logga in")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Användarnamn")
        password = st.text_input("Lösenord", type="password")
        if st.button("Logga in", use_container_width=True):
            if not rate_limit("rl_login", 5, 60):
                st.error("För många försök. Vänta en stund.")
                return
            user, error = login_user(engine, username, password)
            if error == "locked":
                st.error("Kontot är låst. Försök igen senare.")
            elif not user:
                st.error("Fel användarnamn eller lösenord")
            else:
                st.success("Inloggad")
                st.rerun()
    with col2:
        st.markdown("### Skapa konto")
        new_username = st.text_input("Nytt användarnamn")
        new_password = st.text_input("Nytt lösenord", type="password")
        display_name = st.text_input("Visningsnamn (valfritt)")
        st.caption("Användarnamn 3-24 tecken: a-z, 0-9, . _ -")
        st.caption("Lösenord minst 8 tecken")
        if st.button("Skapa konto", use_container_width=True):
            if not rate_limit("rl_register", 3, 300):
                st.error("För många kontoförsök. Vänta en stund.")
                return
            user_id, error = register_user(engine, new_username, new_password, clean_text(display_name, 64) or None)
            if error == "exists":
                st.error("Användarnamnet är upptaget")
            elif error == "invalid_username":
                st.error("Ogiltigt användarnamn")
            elif error == "weak_password":
                st.error("Lösenordet är för kort")
            else:
                st.success("Konto skapat. Logga in.")


def render_set_tile(set_row, owned: int, total: int):
    logo = set_row.get("logo_path") or ""
    symbol = set_row.get("symbol_path") or ""
    logo_html = ""
    symbol_html = ""
    if logo and (logo.startswith("http") or os.path.exists(logo)):
        logo_html = f"<img src='{logo}' alt='{set_row['set_name']}'/>"
    if symbol and (symbol.startswith("http") or os.path.exists(symbol)):
        symbol_html = f"<img src='{symbol}' alt='symbol' style='height:24px;'/>"

    st.markdown(
        f"""
        <div class='set-tile'>
          <div class='set-media'>{logo_html or set_row['set_name']}</div>
          <div class='set-meta'>
            <div class='set-name'>{set_row['set_name']}</div>
            <div class='set-progress'>{owned}/{total}</div>
          </div>
          <div>{symbol_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_card_image(url: str, dim: bool):
    opacity = "0.4" if dim else "1"
    st.markdown(
        f"<img src='{url}' class='card-thumb' style='opacity:{opacity};'/>",
        unsafe_allow_html=True,
    )


def collection_view(user):
    game = st.radio("Välj TCG", ["pokemon"], horizontal=True)
    sets = cached_sets(game)

    if not sets:
        empty_state("Inga set finns ännu. Lägg till set i Admin-sektionen.")
        return

    progress = cached_progress(user["id"], game)
    set_map = {s["id"]: s for s in sets}

    selected_set_id = st.session_state.get("selected_set_id")
    if selected_set_id:
        top = st.columns([1, 2.5, 2])
        with top[0]:
            if st.button("Tillbaka"):
                st.session_state.pop("selected_set_id")
                st.session_state.pop("card_page", None)
                st.rerun()
        selected_set = set_map.get(selected_set_id, {})
        with top[1]:
            st.markdown(f"## {selected_set.get('set_name','Set')}")
        with top[2]:
            search = st.text_input("Sök kort", placeholder="Charizard, 025, Pikachu...", label_visibility="collapsed")
    else:
        top = st.columns([2, 2.5, 1.2])
        sets_count, cards_count = get_db_counts(engine)
        with top[0]:
            st.markdown("## Samling")
            st.caption(f"Databas: {sets_count} set • {cards_count} kort")
        with top[1]:
            set_search = st.text_input("Sök set", placeholder="Skriv setnamn...", label_visibility="collapsed")
        with top[2]:
            if st.button("Uppdatera cache"):
                cached_sets.clear()
                cached_cards.clear()
                cached_progress.clear()
                st.rerun()
        if set_search:
            needle = set_search.strip().lower()
            sets = [s for s in sets if needle in s["set_name"].lower()]

        set_cols = st.columns(3)
        for idx, s in enumerate(sets):
            with set_cols[idx % 3]:
                render_set_tile(s, progress.get(s["id"], 0), s["total_cards"])
                if st.button("Öppna set", key=f"open-set-{s['id']}", use_container_width=True, type="primary"):
                    st.session_state["selected_set_id"] = s["id"]
                    st.rerun()
        return

    cards = cached_cards(selected_set_id)
    cards = sorted(cards, key=lambda c: int(c["card_number"]) if str(c["card_number"]).isdigit() else 999999)
    counts = cached_variant_counts(user["id"], selected_set_id)

    selected_set = set_map.get(selected_set_id, {})
    logo = selected_set.get("logo_path") or ""
    logo_html = f"<img src='{logo}' alt='logo'/>" if logo else ""
    st.markdown(
        f"""
        <div class='set-hero'>
          <div class='set-hero-logo'>{logo_html or selected_set.get('set_name','')}</div>
          <div>
            <div class='set-hero-title'>{selected_set.get('set_name','')}</div>
            <div class='set-hero-sub'>{selected_set.get('series','')}</div>
            <div class='set-hero-row'>
              <div class='chip'>{selected_set.get('total_cards', 0)} kort</div>
              <div class='chip'>Pokémon</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    owned_count = progress.get(selected_set_id, 0)
    total_count = selected_set.get("total_cards", 0)
    if total_count:
        st.caption(f"{owned_count}/{total_count} kort i setet")
        st.progress(min(owned_count / max(total_count, 1), 1.0))
    if search:
        needle = search.strip().lower()
        cards = [
            c for c in cards
            if needle in str(c["name"]).lower() or needle in str(c["card_number"]).lower()
        ]
    if not cards:
        empty_state("Inga kort i detta set ännu.")
        return

    page_size = 60
    card_page = st.session_state.get("card_page", 1)
    total_cards = len(cards)
    cards = cards[: card_page * page_size]

    row = []
    for card in cards:
        variants = []
        if card["has_normal"]:
            variants.append("Normal")
        if card["has_holofoil"]:
            variants.append("Holofoil")
        if card["has_reverse_holo"]:
            variants.append("Reverse Holo")
        for variant in variants:
            row.append((card, variant))

    for i in range(0, len(row), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx >= len(row):
                continue
            card, variant = row[idx]
            count = counts.get(card["id"], {}).get(variant, 0)
            dim = count == 0
            with cols[j]:
                st.markdown("<div class='card-item'>", unsafe_allow_html=True)
                st.markdown(f"<div class='name'>#{card['card_number']} {card['name']}</div>", unsafe_allow_html=True)
                if card.get("rarity"):
                    st.markdown(f"<div class='rarity badge'>{card['rarity']}</div>", unsafe_allow_html=True)
                if card["image_url"]:
                    st.markdown("<div class='card-img'>", unsafe_allow_html=True)
                    render_card_image(card["image_url"], dim)
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='meta'>{variant} • <span class='value'>{str(count).zfill(2)}</span></div>",
                    unsafe_allow_html=True,
                )
                action_cols = st.columns(3)
                with action_cols[0]:
                    if st.button("ℹ", key=f"info-{card['id']}-{variant}"):
                        st.session_state["open_card"] = {**card, "variant": variant, "count": count}
                with action_cols[1]:
                    if st.button("−", key=f"rem-{card['id']}-{variant}"):
                        if not remove_instance(engine, user["id"], card["id"], variant):
                            st.warning("Kortet är låst eller saknas.")
                        cached_cards.clear()
                        cached_progress.clear()
                        st.rerun()
                with action_cols[2]:
                    if st.button("+", key=f"add-{card['id']}-{variant}"):
                        if not add_instance(engine, user["id"], card["id"], variant, "Near Mint", 0.0):
                            st.warning("Den varianten finns inte.")
                        cached_cards.clear()
                        cached_progress.clear()
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    if total_cards > len(cards):
        if st.button("Visa fler kort"):
            st.session_state["card_page"] = card_page + 1
            st.rerun()

    if st.session_state.get("open_card"):
        card = st.session_state["open_card"]
        with st.dialog(f"{card['name']}"):
            st.markdown("<div class='detail-card'>", unsafe_allow_html=True)
            if card.get("image_url"):
                st.image(card["image_url"], use_column_width=True)
            st.markdown(
                "<div class='detail-actions'>"
                "<span class='ghost-btn'>←</span>"
                "<span class='ghost-btn'>⋮</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<div class='detail-title'>{card['name']}</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='detail-sub'>{selected_set.get('set_name','')} • {card.get('rarity') or '—'} • #{card['card_number']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='price-row'>"
                "<span class='ghost-btn'>View Sold Listings</span>"
                "<span class='price'>$0.00</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='price-sub'>Price data placeholder</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='tabs'>"
                "<div class='tab active'>RAW</div>"
                "<div class='tab'>GRADED</div>"
                "<div class='tab'>POP</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='chart'><div class='chart-line'></div></div>",
                unsafe_allow_html=True,
            )
            st.divider()
            st.markdown("### Pris-sökning")
            sources = st.multiselect(
                "Källor",
                ["Cardmarket", "TCGPlayer", "Tradera", "Blocket", "Vinted", "eBay"],
                default=["Cardmarket", "TCGPlayer"],
            )
            query = st.text_input("Sökterm", value=f"{card['name']} {selected_set.get('set_name','')} {card['card_number']}")
            if st.button("Hämta pris"):
                if not rate_limit("rl_price", 20, 60):
                    st.error("För många prisförfrågningar. Vänta lite.")
                    return
                st.session_state["price_results"] = {}
                for src in sources:
                    result = cached_price(src, clean_text(query, 120))
                    st.session_state["price_results"][src] = result

            results = st.session_state.get("price_results", {})
            for src in sources:
                result = results.get(src)
                if not result:
                    continue
                if result.get("error"):
                    st.caption(f"{src}: kunde inte läsa priser ({result['error']}).")
                else:
                    st.markdown(
                        f"**{src}** • Low: {result['low']:.2f} • Median: {result['median']:.2f} • High: {result['high']:.2f}"
                    )
                    if result.get("url"):
                        st.caption(result["url"])
            st.markdown("<div class='pill-row'>", unsafe_allow_html=True)
            st.markdown(f"<span class='badge'>{card['variant']}</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='badge'>Äger {str(card['count']).zfill(2)}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("#### Pris för kortet")
            paid = st.number_input("Pris du betalade (SEK)", min_value=0.0, step=1.0, key=f"paid-{card['id']}-{card['variant']}")
            if st.button("Lägg till kort med pris", key=f"addpaid-{card['id']}-{card['variant']}"):
                if not add_instance(engine, user["id"], card["id"], card["variant"], "Near Mint", paid):
                    st.warning("Den varianten finns inte.")
                cached_cards.clear()
                cached_progress.clear()
                st.rerun()
            if st.button("Uppdatera senaste pris", key=f"upprice-{card['id']}-{card['variant']}"):
                if not update_purchase_price(engine, user["id"], card["id"], card["variant"], paid):
                    st.warning("Hittade inget kort att uppdatera.")
                st.rerun()
            if st.button("Stäng"):
                st.session_state.pop("open_card")
                st.rerun()


def render_room_view(furniture, items):
    html = ["<div class='room-wrap'><div class='room'>"]
    html.append("<div class='room-ceil'></div>")
    html.append("<div class='room-wall wall-left'></div>")
    html.append("<div class='room-wall wall-back'></div>")
    html.append("<div class='room-wall wall-right'></div>")
    html.append("<div class='room-floor'></div>")

    for f in furniture:
        fclass = "shelf" if f["type"] == "SHELF" else "table" if f["type"] == "TABLE" else "stand"
        html.append(
            f"<div class='furniture {fclass}' style='left:{f['x_pos']}%; top:{f['y_pos']}%;'></div>"
        )

    for i in items:
        html.append(
            f"<div class='room-card' style='left:{i['x_pos']}%; top:{i['y_pos']}%;'>"
            f"<img src='{i['image_url']}' />"
            f"</div>"
        )

    html.append("</div></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def room_view(user):
    st.markdown("## Mitt Rum")
    tabs = st.tabs(["Min room", "Profilvy"])
    with tabs[0]:
        furniture = get_furniture(engine, user["id"])
        room_items = get_room_items(engine, user["id"], public_only=False)
        render_room_view(furniture, room_items)

        st.markdown("### Lägg till möbel")
        f_type = st.selectbox("Möbeltyp", ["SHELF", "TABLE", "STAND"])
        fx = st.slider("X (%)", 0, 90, 10)
        fy = st.slider("Y (%)", 0, 90, 60)
        if st.button("Placera möbel"):
            add_furniture(engine, user["id"], f_type, fx, fy)
            st.rerun()

        st.markdown("### Placera kort på möbel")
        available = get_available_items(engine, user["id"])
        if not available:
            empty_state("Inga kort att placera. Lägg till kort i Samling.")
        item_options = {f"{row['name']} #{row['card_number']}": row["item_id"] for row in available}
        furniture_options = {f"{f['type']} ({f['id']})": f["id"] for f in furniture}
        selected_item = st.selectbox("Kort", ["--"] + list(item_options.keys()))
        selected_furn = st.selectbox("Möbel", ["--"] + list(furniture_options.keys()))
        cx = st.slider("Kort X (%)", 0, 90, 30)
        cy = st.slider("Kort Y (%)", 0, 90, 40)
        if st.button("Placera kort") and selected_item != "--":
            fid = furniture_options.get(selected_furn) if selected_furn != "--" else None
            place_item(engine, user["id"], item_options[selected_item], "ROOM", cx, cy, furniture_id=fid)
            st.rerun()

    with tabs[1]:
        st.markdown("### Publik profil")
        username = st.text_input("Användarnamn")
        if st.button("Visa profil") and username:
            user_row = get_user_by_username(engine, username)
            if not user_row:
                st.error("Ingen användare hittades")
            else:
                public_items = get_room_items(engine, user_row["id"], public_only=True)
                furniture = get_furniture(engine, user_row["id"])
                render_room_view(furniture, public_items)

                st.markdown("### Kort i rummet")
                for c in public_items:
                    if st.button(f"{c['name']} #{c['card_number']}", key=f"pub-{c['room_item_id']}"):
                        st.session_state["open_card"] = {**c, "variant": "Normal", "count": 0}


def market_view(user):
    st.markdown("## Marknad")
    listings = list_listings(engine)

    st.markdown("### Aktiva annonser")
    if not listings:
        empty_state("Inga annonser just nu.")
    cols = st.columns(3)
    for i, row in enumerate(listings):
        with cols[i % 3]:
            if row.get("image_url"):
                st.image(row["image_url"], use_column_width=True)
            st.markdown(f"**{row['name']} #{row['card_number']}**")
            st.caption(f"Säljare: {row['seller']}")
            st.caption(f"Pris: {row['price']} {row['currency']}")
            st.caption(row.get("notes") or "")
            if row["seller"] == user["username"]:
                if st.button("Ta bort", key=f"close-{row['id']}"):
                    close_listing(engine, row["id"], user["id"])
                    st.rerun()
            else:
                if st.button("Visa intresse", key=f"interest-{row['id']}"):
                    create_interest(engine, row["id"], user["id"])
                    st.success("Intresse skickat")

    st.markdown("### Skapa annons")
    item_id = st.text_input("Card instance ID")
    price = st.number_input("Pris", min_value=0.0, step=1.0)
    currency = st.text_input("Valuta", value="SEK")
    notes = st.text_area("Beskrivning")
    if st.button("Skapa annons"):
        err = create_listing(engine, user["id"], item_id, price, currency, notes)
        if err == "not_owner":
            st.error("Du äger inte kortet")
        elif err == "not_verified":
            st.error("Kortet måste vara verifierat")
        elif err == "locked":
            st.error("Kortet är låst")
        else:
            st.success("Annons skapad")
            st.rerun()

    st.markdown("### Intressen")
    interests = list_interests_for_seller(engine, user["id"])
    if not interests:
        st.caption("Inga intressen ännu.")
    for interest in interests:
        st.markdown(f"**{interest['buyer']}** vill köpa {interest['name']} #{interest['card_number']}")
        if st.button("Acceptera", key=f"acc-{interest['id']}"):
            update_interest(engine, interest["id"], user["id"], "ACCEPTED")
            st.success("Accepterad")
            st.rerun()
        if st.button("Avslå", key=f"dec-{interest['id']}"):
            update_interest(engine, interest["id"], user["id"], "DECLINED")
            st.rerun()

    st.markdown("### Transaktioner")
    txs = list_transactions(engine, user["id"])
    if not txs:
        st.caption("Inga transaktioner ännu.")
    for tx in txs:
        st.markdown(f"**{tx['name']} #{tx['card_number']}** • {tx['status']}")
        if st.button("Markera som skickad", key=f"ship-{tx['id']}"):
            update_transaction(engine, tx["id"], user["id"], "SHIPPED")
            st.rerun()
        if st.button("Markera som mottagen", key=f"recv-{tx['id']}"):
            update_transaction(engine, tx["id"], user["id"], "COMPLETED")
            st.rerun()


def groups_view(user):
    st.markdown("## Social Hubb")

    left, right = st.columns([2, 3])
    with left:
        st.markdown("### Grupper")
        groups = list_groups(engine)
        if not groups:
            empty_state("Inga grupper än. Skapa en ny.")
        for g in groups:
            col = st.columns([3, 1, 1])
            with col[0]:
                st.markdown(f"**{g['name']}**")
                st.caption(g.get("description") or "")
            with col[1]:
                st.caption(f"{g['members']} medlemmar")
            with col[2]:
                if st.button("Öppna", key=f"open-{g['id']}"):
                    st.session_state["active_group"] = g["id"]
                    st.rerun()

        st.markdown("#### Skapa grupp")
        name = st.text_input("Gruppnamn")
        desc = st.text_input("Beskrivning")
        if st.button("Skapa") and name:
            create_group(engine, clean_text(name, 80), clean_text(desc or "", 200) or None)
            st.rerun()

    with right:
        group_id = st.session_state.get("active_group")
        if not group_id:
            st.info("Välj en grupp till höger.")
            return

        member = is_member(engine, group_id, user["id"])
        if not member:
            if st.button("Gå med i grupp"):
                join_group(engine, group_id, user["id"])
                st.rerun()
            st.warning("Du måste gå med för att se innehåll.")
            return

        tabs = st.tabs(["Inlägg", "Sälj", "Byte", "Köp", "Chatt"])
        categories = {"Inlägg": "POST", "Sälj": "SELL", "Byte": "TRADE", "Köp": "BUY"}

        for tab in tabs:
            with tab:
                if tab.label == "Chatt":
                    st.info("Chatt byggs nu.")
                    continue
                category = categories.get(tab.label)
                posts = list_posts(engine, group_id, category)
                if not posts:
                    st.caption("Inga inlägg ännu.")
                for post in posts:
                    st.markdown(f"**{post['username']}** • {post['created_at']}")
                    st.write(post["content"])
                    if post.get("offered_name"):
                        st.caption(f"Erbjuder: {post['offered_name']} #{post['offered_number']}")
                    if st.button("Ta bort", key=f"del-{post['id']}"):
                        delete_post(engine, post["id"], user["id"])
                        st.rerun()

                st.markdown("#### Skapa inlägg")
                content = st.text_area("Text", key=f"content-{tab.label}")
                trade_type = None
                offered_item_id = None
                requested_card_id = None
                if category in ["SELL", "TRADE", "BUY"]:
                    trade_type = st.selectbox("Trade type", ["SPECIFIC", "MULTI", "RANDOM"], key=f"trade-{tab.label}") if category == "TRADE" else None
                    offered_item_id = st.text_input("Offered item id", key=f"offer-{tab.label}")
                    requested_card_id = st.text_input("Requested card id", key=f"req-{tab.label}")

                if st.button("Publicera", key=f"post-{tab.label}"):
                    err = create_post(engine, group_id, user["id"], category, clean_text(content, 800), trade_type, offered_item_id, requested_card_id)
                    if err == "not_owner":
                        st.error("Du äger inte kortet")
                    elif err == "not_verified":
                        st.error("Kortet måste vara verifierat")
                    elif err == "locked":
                        st.error("Kortet är låst")
                    else:
                        st.success("Publicerat")
                        st.rerun()


def sealed_view(user):
    st.markdown("## Sealed")
    tabs = st.tabs(["Produkter", "Mina Sealed", "Öppna Booster", "Öppningshistorik"])

    with tabs[0]:
        products = list_sealed_products(engine, "pokemon")
        if not products:
            empty_state("Inga sealed produkter ännu. Lägg till via Admin.")
        for p in products:
            st.markdown("<div class='card-item'>", unsafe_allow_html=True)
            st.markdown(f"<div class='name'>{p['name']}</div>", unsafe_allow_html=True)
            if p.get("image_url"):
                st.markdown("<div class='card-img'>", unsafe_allow_html=True)
                st.image(p["image_url"], use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>{p['type']} • {p.get('set_id') or 'Set saknas'}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("### Lägg till sealed du äger")
        products = list_sealed_products(engine, "pokemon")
        options = {f"{p['name']} ({p['type']})": p["id"] for p in products}
        prod = st.selectbox("Produkt", ["--"] + list(options.keys()))
        price = st.number_input("Pris (SEK)", min_value=0.0, value=0.0, step=1.0)
        pdate = st.date_input("Köpdatum", value=None)
        notes = st.text_area("Anteckningar")
        if st.button("Lägg till") and prod != "--":
            add_sealed_instance(engine, user["id"], options[prod], price, pdate, clean_text(notes or "", 300) or None)
            st.success("Tillagd")

        st.divider()
        st.markdown("### Mina sealed")
        owned = list_user_sealed(engine, user["id"])
        if not owned:
            st.caption("Inga sealed ännu.")
        for item in owned:
            st.markdown("<div class='card-item'>", unsafe_allow_html=True)
            st.markdown(f"<div class='name'>{item['name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>{item['type']} • {item['state']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>Pris: {item['purchase_price']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("### Öppna booster (manual)")
        owned = [i for i in list_user_sealed(engine, user["id"]) if i["state"] == "SEALED" and i["type"] == "BOOSTER_PACK"]
        if not owned:
            st.caption("Inga booster packs att öppna.")
            return
        options = {f"{i['name']} ({i['id']})": i["id"] for i in owned}
        selected = st.selectbox("Välj booster", list(options.keys()))
        st.markdown("<div class='pack-row'>", unsafe_allow_html=True)
        st.markdown("<div class='pack'><div class='pack-strip'></div></div>", unsafe_allow_html=True)
        st.markdown("<div class='pack-title'>10 kort kommer visas här efter öppning</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        card_numbers = []
        variants_list = []
        st.markdown("Fyll i 10 kortnummer:")
        cols = st.columns(5)
        for i in range(10):
            with cols[i % 5]:
                card_numbers.append(st.text_input(f"#{i+1}", key=f"bn-{i}"))
                variants_list.append(st.selectbox("Variant", ["Normal", "Holofoil", "Reverse Holo"], key=f"bv-{i}"))
        if st.button("Öppna booster"):
            nums = [n.strip() for n in card_numbers if n.strip()]
            result, opening_id = open_booster(engine, user["id"], options[selected], nums, variants_list)
            if result == "ok":
                st.success("Booster öppnad!")
                cards = list_opening_cards(engine, opening_id)
                st.markdown("### Dina 10 kort")
                st.markdown("<div class='slot-grid'>", unsafe_allow_html=True)
                for c in cards:
                    st.markdown("<div class='slot animate-card'>", unsafe_allow_html=True)
                    if c.get("image_url"):
                        st.image(c["image_url"], use_column_width=True)
                    st.caption(f"{c['name']} #{c['card_number']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error(f"Fel: {result}")

    with tabs[3]:
        openings = list_openings(engine, user["id"])
        if not openings:
            st.caption("Inga öppningar ännu.")
        for o in openings:
            st.markdown("<div class='card-item'>", unsafe_allow_html=True)
            st.markdown(f"<div class='name'>{o['sealed_name']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>Öppnad: {o['opened_at']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta'>Spent: {o['total_spent']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


def budget_view(user):
    st.markdown("## Analys")
    tabs = st.tabs(["Budget", "Flipping", "Säljassistent"])

    with tabs[0]:
        with engine.begin() as conn:
            spent_cards = conn.execute(text("SELECT SUM(purchase_price) FROM card_instances WHERE owner_id=:u"), {"u": user["id"]}).scalar() or 0
            spent_sealed = conn.execute(text("SELECT SUM(purchase_price) FROM sealed_instances WHERE owner_id=:u"), {"u": user["id"]}).scalar() or 0
        total_spent = float(spent_cards) + float(spent_sealed)
        st.metric("Totalt spenderat", f"{total_spent:.2f} SEK")
        st.metric("Kort", f"{float(spent_cards):.2f} SEK")
        st.metric("Sealed", f"{float(spent_sealed):.2f} SEK")

    with tabs[1]:
        st.markdown("### Flipping Dashboard")
        fee = st.slider("Plattformsavgift %", min_value=0, max_value=20, value=10, step=1)
        source = st.selectbox("Pris-källa", ["Cardmarket", "TCGPlayer", "Tradera", "Blocket", "Vinted", "eBay"])
        run = st.button("Analysera")
        if run:
            rows = list_owned_cards(engine, user["id"])
            for r in rows[:100]:
                if not r.get("purchase_price"):
                    continue
                query = f"{r['name']} {r.get('set_name','')} {r['card_number']}"
                result = cached_price(source, query)
                if result.get("error"):
                    st.caption(f"{r['name']}: ingen prisdata")
                    continue
                median = result.get("median", 0)
                break_even = float(r["purchase_price"]) / (1 - fee / 100) if fee < 100 else 0
                color = "🟢" if median >= break_even else "🔴"
                st.markdown(f"{color} **{r['name']}** • Betalt: {r['purchase_price']} • Median: {median:.2f} • Break-even: {break_even:.2f}")

    with tabs[2]:
        st.markdown("### Smart Price Suggester")
        rows = list_owned_cards(engine, user["id"])
        options = {f"{r['name']} #{r['card_number']} ({r.get('set_name','')})": r for r in rows}
        if not options:
            st.caption("Inga kort ännu.")
        else:
            selected_label = st.selectbox("Välj kort", list(options.keys()))
            selected = options[selected_label]
            source = st.selectbox("Pris-källa", ["Cardmarket", "TCGPlayer", "Tradera", "Blocket", "Vinted", "eBay"], key="sugg-source")
            query = f"{selected['name']} {selected.get('set_name','')} {selected['card_number']}"
            if st.button("Hämta pris"):
                result = cached_price(source, query)
                if result.get("error"):
                    st.error("Ingen prisdata")
                else:
                    low = result.get("low", 0)
                    median = result.get("median", 0)
                    high = result.get("high", 0)
                    st.metric("Quick Sale", f"{max(low * 0.95, 0):.2f}")
                    st.metric("Fair Market", f"{median:.2f}")
                    st.metric("High-End", f"{high:.2f}")


def admin_view(user):
    st.markdown("## Admin / Import")
    if not require_admin(user):
        st.error("Du saknar behörighet.")
        return

    st.markdown("Här lägger du till set och kort tills automatiska importer är klara.")

    with st.form("add_set"):
        st.subheader("Lägg till set")
        game = st.selectbox("Game", ["pokemon"], index=0)
        set_name = st.text_input("Set namn")
        series = st.text_input("Serie / Era")
        set_code = st.text_input("Set code (valfritt)")
        total = st.number_input("Totalt antal kort", min_value=0, step=1)
        logo_path = st.text_input("Logo path (assets/Logos/...)")
        symbol_path = st.text_input("Symbol path (assets/Set Symbols/...)")
        submitted = st.form_submit_button("Spara set")
        if submitted and set_name:
            import sqlalchemy as sa
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO tcg_sets (id, game, series, set_name, set_code, total_cards, logo_path, symbol_path)
                        VALUES (:id, :g, :s, :n, :c, :t, :l, :sym)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "g": game,
                        "s": series,
                        "n": set_name,
                        "c": set_code,
                        "t": int(total),
                        "l": logo_path or None,
                        "sym": symbol_path or None,
                    },
                )
            st.success("Set sparat")

    with st.form("add_card"):
        st.subheader("Lägg till kort")
        set_id = st.text_input("Set ID")
        card_number = st.text_input("Kortnummer")
        card_name = st.text_input("Kortnamn")
        image_url = st.text_input("Bild URL")
        rarity = st.text_input("Rarity")
        has_normal = st.checkbox("Normal", value=True)
        has_holo = st.checkbox("Holofoil")
        has_reverse = st.checkbox("Reverse Holo")
        submitted = st.form_submit_button("Spara kort")
        if submitted and set_id and card_name:
            import sqlalchemy as sa
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO tcg_cards (id, set_id, card_number, name, rarity, image_url, has_normal, has_holofoil, has_reverse_holo)
                        VALUES (:id, :sid, :num, :name, :rar, :img, :hn, :hh, :hr)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "sid": set_id,
                        "num": card_number,
                        "name": card_name,
                        "rar": rarity,
                        "img": image_url or None,
                        "hn": 1 if has_normal else 0,
                        "hh": 1 if has_holo else 0,
                        "hr": 1 if has_reverse else 0,
                    },
                )
            st.success("Kort sparat")

    with st.form("import_card"):
        st.subheader("Importera från pokemon.com")
        set_id = st.text_input("Set ID (för databasen)")
        set_code = st.text_input("Set code (t.ex. me01)")
        card_number = st.text_input("Kortnummer (t.ex. 36)")
        submitted = st.form_submit_button("Hämta och spara")
        if submitted and set_id and set_code and card_number:
            data = fetch_pokemon_card(set_code, card_number)
            if not data:
                st.error("Kunde inte hämta kortet")
            else:
                import sqlalchemy as sa
                with engine.begin() as conn:
                    conn.execute(
                        sa.text(
                            """
                            INSERT INTO tcg_cards (id, set_id, card_number, name, rarity, image_url, has_normal, has_holofoil, has_reverse_holo)
                            VALUES (:id, :sid, :num, :name, :rar, :img, :hn, :hh, :hr)
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "sid": set_id,
                            "num": card_number,
                            "name": data.get("name"),
                            "rar": data.get("rarity"),
                            "img": data.get("image_url"),
                            "hn": 1,
                            "hh": 1 if data.get("rarity", "").lower().find("holo") >= 0 else 0,
                            "hr": 0,
                        },
                    )
                st.success("Kort importerat")

    st.divider()
    st.subheader("Bulkimport från Pokémon TCG API")
    st.caption("Importer sker i små batcher för att undvika timeouts på Streamlit Cloud.")
    mode = st.selectbox("Typ", ["Importera set", "Importera kort (sida)", "Importera kort för set"])
    if mode == "Importera set":
        if st.button("Hämta och spara set"):
            sets = fetch_sets()
            count = upsert_sets(engine, sets)
            st.success(f"Sparade {count} set.")
    elif mode == "Importera kort (sida)":
        page = st.number_input("Page", min_value=1, value=1, step=1)
        page_size = st.number_input("Page size", min_value=10, max_value=250, value=250, step=10)
        if st.button("Hämta sida"):
            data = fetch_cards_page(int(page), int(page_size))
            cards = data.get("data", [])
            count = upsert_cards(engine, cards)
            st.success(f"Sparade {count} kort.")
    else:
        set_id = st.text_input("Set ID (t.ex. swsh4)")
        page = st.number_input("Page", min_value=1, value=1, step=1, key="set-page")
        page_size = st.number_input("Page size", min_value=10, max_value=250, value=250, step=10, key="set-size")
        if st.button("Hämta set-kort") and set_id:
            data = fetch_cards_page(int(page), int(page_size), query=f"set.id:{set_id}")
            cards = data.get("data", [])
            count = upsert_cards(engine, cards)
            st.success(f"Sparade {count} kort för {set_id}.")

    st.caption("För full import rekommenderas CLI-skriptet scripts/import_pokemon_api.py (kör lokalt).")

    st.divider()
    st.subheader("Importera från pokemon.com (expansion)")
    st.caption("Använder expansion-kod (t.ex. me01). Importerar kortens namn/bild/nummer.")
    expansion = st.text_input("Expansion code", key="pokemoncom-exp")
    delay = st.slider("Delay per card (sek)", min_value=0.2, max_value=2.0, value=0.4, step=0.1)
    if st.button("Importera från pokemon.com") and expansion:
        result = import_set_from_pokemon_com(engine, expansion, delay=delay)
        st.success(f"Hämtade {result['links']} länkar. Sparade {result['imported']} kort.")

    st.divider()
    st.subheader("Sealed produkter (admin)")
    with st.form("add_sealed"):
        pid = st.text_input("ID (unik)", help="t.ex. pkm_booster_pack_sv4")
        name = st.text_input("Namn")
        set_id = st.text_input("Set ID (valfritt)")
        type_label = st.selectbox("Typ", ["BOOSTER_PACK", "BOOSTER_BOX", "ETB", "TINS"])
        image_url = st.text_input("Bild URL")
        cards_per_pack = st.number_input("Kort per pack", min_value=1, value=10, step=1)
        msrp = st.number_input("MSRP", min_value=0.0, value=0.0, step=1.0)
        submitted = st.form_submit_button("Spara sealed")
        if submitted and pid and name:
            create_sealed_product(engine, pid, "pokemon", type_label, set_id or None, name, image_url or None, int(cards_per_pack), msrp or None)
            st.success("Sealed produkt sparad")

    if st.button("Hämta featured products (scrape)"):
        items = scrape_featured_products()
        st.success(f"Hittade {len(items)} produkter (granska och spara manuellt).")
        for item in items[:20]:
            st.write(item["name"])


def main():
    header()

    user = get_current_user()
    if not user:
        login_view()
        return

    with st.sidebar:
        st.markdown("<div class='sidebar-brand'>CollectorHub</div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-title'>Inloggad</div>", unsafe_allow_html=True)
        initials = user["username"][:1].upper()
        st.markdown(f"<div class='sidebar-user'><div class='avatar'>{initials}</div><div><strong>{user['username']}</strong></div></div>", unsafe_allow_html=True)
        if st.button("Logga ut"):
            logout_user()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-card' style='margin-top:12px;'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-title'>Navigering</div>", unsafe_allow_html=True)
        pages = ["Samling", "Sealed", "Marknad", "Social Hubb", "Mitt Rum", "Budget"]
        if require_admin(user):
            pages.append("Admin")
        page = st.radio("Navigering", pages, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    page_label = page.split(" ", 1)[1] if " " in page else page

    if page_label == "Samling":
        collection_view(user)
    elif page_label == "Sealed":
        sealed_view(user)
    elif page_label == "Marknad":
        market_view(user)
    elif page_label == "Social Hubb":
        groups_view(user)
    elif page_label == "Mitt Rum":
        room_view(user)
    elif page_label == "Budget":
        budget_view(user)
    elif page_label == "Admin":
        admin_view(user)


if __name__ == "__main__":
    main()
