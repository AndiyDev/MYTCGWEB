import os
import uuid
import streamlit as st
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
)
from lib.pokemon_import import fetch_pokemon_card
from lib.pokemon_api import fetch_sets, fetch_cards_page
from lib.import_pokemon import upsert_sets, upsert_cards
from lib.pokemon_com import import_set_from_pokemon_com
from lib.pricing import scrape_source
from lib.room import get_room_items, get_available_items, place_item, clear_slot, get_user_by_username
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
  --bg: #0a0a0f;
  --panel: #14141b;
  --panel-2: #101018;
  --stroke: #2b2b36;
  --accent: #6df2d7;
  --accent-2: #56a2ff;
  --text: #e7e9ee;
  --muted: #9aa0a6;
}

html, body, [class*="css"]  { font-family: 'Space Grotesk', sans-serif; }
body {
  background:
    radial-gradient(900px 420px at 10% -10%, #1b1b28 0%, #0a0a0f 60%),
    radial-gradient(900px 420px at 110% 0%, #10223a 0%, #0a0a0f 55%);
  color: var(--text);
}
section[data-testid="stSidebar"] { background: #12121a; border-right: 1px solid var(--stroke); }
section[data-testid="stSidebar"] .stRadio > div { gap: 0.35rem; }
section[data-testid="stSidebar"] label { color: var(--text) !important; }
section[data-testid="stSidebar"] .stButton > button { width: 100%; }
section[data-testid="stSidebar"] .sidebar-card { background: #171725; border: 1px solid var(--stroke); padding: 12px; border-radius: 14px; }
section[data-testid="stSidebar"] .sidebar-title { font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }

div[data-testid="stVerticalBlock"] { gap: 1rem; }

.card { background: var(--panel); border: 1px solid var(--stroke); padding: 14px; border-radius: 14px; box-shadow: 0 10px 28px rgba(0,0,0,0.3); }
.section-title { font-size: 22px; font-weight: 700; margin: 10px 0; }

.stButton > button {
  border-radius: 10px; border: 1px solid var(--stroke);
  background: linear-gradient(180deg, #1a1a26 0%, #12121a 100%);
  color: var(--text); padding: 0.6rem 0.9rem;
}
.stButton > button:hover { border-color: #3a3a48; background: #1f1f2b; }
.stButton > button:focus { box-shadow: 0 0 0 2px rgba(109,242,215,0.25); }
input, textarea, select { border-radius: 10px !important; }

.muted { color: var(--muted); }

.collection-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(220px,1fr)); gap: 16px; }
.card-item {
  background: var(--panel-2);
  border: 1px solid var(--stroke);
  border-radius: 16px;
  padding: 12px;
  box-shadow: 0 12px 28px rgba(0,0,0,0.35);
}
.card-item .card-img {
  background: #0d0d12;
  border: 1px solid #232332;
  border-radius: 14px;
  padding: 8px;
  margin-bottom: 10px;
}
.card-item .name { font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; }
.card-item .meta { color: var(--muted); font-size: 0.85rem; margin-top: 6px; }
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
            user_id, error = register_user(engine, new_username, new_password, display_name or None)
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
    if logo and (logo.startswith("http") or os.path.exists(logo)):
        st.image(logo, use_column_width=True)
    else:
        st.markdown(f"**{set_row['set_name']}**")
    if symbol and (symbol.startswith("http") or os.path.exists(symbol)):
        st.image(symbol, width=32)
    st.caption(f"{str(owned).zfill(3)}/{str(total).zfill(3)}")


def render_card_image(url: str, dim: bool):
    if dim:
        st.markdown(
            f"<img src='{url}' style='width:100%; opacity:0.4; border-radius:10px;'/>",
            unsafe_allow_html=True,
        )
    else:
        st.image(url, use_column_width=True)


def collection_view(user):
    st.markdown("## Samling")
    game = st.radio("Välj TCG", ["pokemon"], horizontal=True)
    sets = cached_sets(game)

    if not sets:
        empty_state("Inga set finns ännu. Lägg till set i Admin-sektionen.")
        return

    progress = cached_progress(user["id"], game)
    set_map = {s["id"]: s for s in sets}

    if st.session_state.get("selected_set_id"):
        if st.button("Tillbaka till set"):
            st.session_state.pop("selected_set_id")
            st.rerun()

    set_cols = st.columns(4)
    selected_set_id = st.session_state.get("selected_set_id")
    for idx, s in enumerate(sets):
        with set_cols[idx % 4]:
            clicked = st.button(s["set_name"], use_container_width=True)
            render_set_tile(s, progress.get(s["id"], 0), s["total_cards"])
            if clicked:
                st.session_state["selected_set_id"] = s["id"]
                st.rerun()

    if not selected_set_id:
        return

    cards = cached_cards(selected_set_id)
    cards = sorted(cards, key=lambda c: int(c["card_number"]) if str(c["card_number"]).isdigit() else 999999)
    counts = get_user_variant_counts(engine, user["id"], selected_set_id)

    st.markdown("### Kort i set")
    selected_set = set_map.get(selected_set_id, {})
    search = st.text_input("Sök kort (namn eller nummer)")
    filter_variants = st.multiselect("Filter", ["Normal", "Holofoil", "Reverse Holo"], default=["Normal", "Holofoil", "Reverse Holo"])
    if search:
        needle = search.strip().lower()
        cards = [
            c for c in cards
            if needle in str(c["name"]).lower() or needle in str(c["card_number"]).lower()
        ]
    if not cards:
        empty_state("Inga kort i detta set ännu.")
        return

    st.markdown("<div class='collection-grid'>", unsafe_allow_html=True)
    for i, card in enumerate(cards):
        variants = []
        if card["has_normal"]:
            variants.append("Normal")
        if card["has_holofoil"]:
            variants.append("Holofoil")
        if card["has_reverse_holo"]:
            variants.append("Reverse Holo")

        for variant in variants:
            count = counts.get(card["id"], {}).get(variant, 0)
            dim = count == 0
            if variant not in filter_variants:
                continue
            st.markdown("<div class='card-item'>", unsafe_allow_html=True)
            st.markdown(f"<div class='name'>#{card['card_number']} {card['name']}</div>", unsafe_allow_html=True)
            if card["image_url"]:
                st.markdown("<div class='card-img'>", unsafe_allow_html=True)
                render_card_image(card["image_url"], dim)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='meta'>{selected_set.get('set_name','')} • {variant} • <span class='value'>{str(count).zfill(2)}</span></div>",
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            with cols[0]:
                if st.button("Info", key=f"info-{card['id']}-{variant}"):
                    st.session_state["open_card"] = {**card, "variant": variant, "count": count}
            with cols[1]:
                if st.button("-", key=f"rem-{card['id']}-{variant}"):
                    if not remove_instance(engine, user["id"], card["id"], variant):
                        st.warning("Kortet är låst eller saknas.")
                    cached_cards.clear()
                    cached_progress.clear()
                    st.rerun()
            with cols[2]:
                if st.button("+", key=f"add-{card['id']}-{variant}"):
                    if not add_instance(engine, user["id"], card["id"], variant, "Near Mint"):
                        st.warning("Den varianten finns inte.")
                    cached_cards.clear()
                    cached_progress.clear()
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

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
                st.session_state["price_results"] = {}
                for src in sources:
                    result = cached_price(src, query)
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
            if st.button("Stäng"):
                st.session_state.pop("open_card")
                st.rerun()


def render_room_grid(items_by_slot, slots, title):
    st.markdown(f"### {title}")
    cols = st.columns(len(slots))
    for idx, slot in enumerate(slots):
        with cols[idx]:
            item = items_by_slot.get(slot)
            if item:
                st.image(item["image_url"], use_column_width=True)
                st.caption(f"{item['name']} #{item['card_number']}")
            else:
                st.markdown("<div style='height:120px; border:1px dashed #333; border-radius:8px;'></div>", unsafe_allow_html=True)
            st.caption(f"Slot {slot}")


def room_view(user):
    st.markdown("## Mitt Rum")
    tabs = st.tabs(["Min room", "Profilvy"])
    with tabs[0]:
        available = get_available_items(engine, user["id"])
        room_items = get_room_items(engine, user["id"], public_only=False)
        items_by_slot = {f"{r['slot_type']}-{r['x_pos']}-{r['y_pos']}": r for r in room_items}

        st.markdown("### Placera kort")
        if not available:
            empty_state("Inga kort att placera. Lägg till kort i Samling.")
        item_options = {f"{row['name']} #{row['card_number']}": row["item_id"] for row in available}
        slot_type = st.selectbox("Möbel", ["Wall-Left", "Wall-Right", "Center-Stand"])
        x_pos = st.number_input("X", value=1)
        y_pos = st.number_input("Y", value=1)
        selected_item = st.selectbox("Kort", ["--" ] + list(item_options.keys()))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Placera") and selected_item != "--":
                place_item(engine, user["id"], item_options[selected_item], slot_type, x_pos, y_pos)
                st.rerun()
        with col2:
            if st.button("Ta bort från slot"):
                clear_slot(engine, user["id"], slot_type, x_pos, y_pos)
                st.rerun()

        render_room_grid(items_by_slot, ["Wall-Left-1-1", "Wall-Left-2-1", "Wall-Left-3-1"], "Vänster vägg")
        render_room_grid(items_by_slot, ["Center-Stand-1-1", "Center-Stand-2-1", "Center-Stand-3-1"], "Ställ i mitten")
        render_room_grid(items_by_slot, ["Wall-Right-1-1", "Wall-Right-2-1", "Wall-Right-3-1"], "Höger vägg")

    with tabs[1]:
        st.markdown("### Publik profil")
        username = st.text_input("Användarnamn")
        if st.button("Visa profil") and username:
            user_row = get_user_by_username(engine, username)
            if not user_row:
                st.error("Ingen användare hittades")
            else:
                public_items = get_room_items(engine, user_row["id"], public_only=True)
                items_by_slot = {f"{r['slot_type']}-{r['x_pos']}-{r['y_pos']}": r for r in public_items}
                render_room_grid(items_by_slot, ["Wall-Left-1-1", "Wall-Left-2-1", "Wall-Left-3-1"], "Vänster vägg")
                render_room_grid(items_by_slot, ["Center-Stand-1-1", "Center-Stand-2-1", "Center-Stand-3-1"], "Ställ i mitten")
                render_room_grid(items_by_slot, ["Wall-Right-1-1", "Wall-Right-2-1", "Wall-Right-3-1"], "Höger vägg")


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
            create_group(engine, name, desc or None)
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
                    err = create_post(engine, group_id, user["id"], category, content, trade_type, offered_item_id, requested_card_id)
                    if err == "not_owner":
                        st.error("Du äger inte kortet")
                    elif err == "not_verified":
                        st.error("Kortet måste vara verifierat")
                    elif err == "locked":
                        st.error("Kortet är låst")
                    else:
                        st.success("Publicerat")
                        st.rerun()


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


def main():
    header()

    user = get_current_user()
    if not user:
        login_view()
        return

    with st.sidebar:
        st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-title'>Inloggad</div>", unsafe_allow_html=True)
        st.markdown(f"**{user['username']}**")
        if st.button("Logga ut"):
            logout_user()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-card' style='margin-top:12px;'>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-title'>Navigering</div>", unsafe_allow_html=True)
        pages = ["Samling", "Marknad", "Social Hubb", "Mitt Rum"]
        if require_admin(user):
            pages.append("Admin")
        page = st.radio("Navigering", pages)
        st.markdown("</div>", unsafe_allow_html=True)

    if page == "Samling":
        collection_view(user)
    elif page == "Marknad":
        market_view(user)
    elif page == "Social Hubb":
        groups_view(user)
    elif page == "Mitt Rum":
        room_view(user)
    elif page == "Admin":
        admin_view(user)


if __name__ == "__main__":
    main()
