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

st.set_page_config(page_title="MYTCGWEB", layout="wide")

engine = get_engine()
init_schema(engine)


def header():
    st.markdown("# MYTCGWEB")


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
        if st.button("Skapa konto", use_container_width=True):
            created = register_user(engine, new_username, new_password, display_name or None)
            if not created:
                st.error("Användarnamnet är upptaget")
            else:
                st.success("Konto skapat. Logga in.")


def render_set_tile(set_row, owned: int, total: int):
    logo = set_row.get("logo_path") or ""
    symbol = set_row.get("symbol_path") or ""
    if logo and os.path.exists(logo):
        st.image(logo, use_column_width=True)
    else:
        st.markdown(f"**{set_row['set_name']}**")
    if symbol and os.path.exists(symbol):
        st.image(symbol, width=32)
    st.caption(f"{str(owned).zfill(3)}/{str(total).zfill(3)}")


def render_card_image(url: str, dim: bool):
    if dim:
        st.markdown(
            f"<img src='{url}' style='width:100%; opacity:0.4; border-radius:6px;'/>",
            unsafe_allow_html=True,
        )
    else:
        st.image(url, use_column_width=True)


def collection_view(user):
    st.markdown("## Samling")
    game = st.radio("Välj TCG", ["pokemon"], horizontal=True)
    sets = get_sets(engine, game)

    if not sets:
        st.info("Inga set finns ännu. Lägg till set i Admin-sektionen.")
        return

    progress = get_set_progress(engine, user["id"], game)

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

    cards = get_cards_for_set(engine, selected_set_id)
    counts = get_user_variant_counts(engine, user["id"], selected_set_id)

    st.markdown("### Kort i set")
    grid = st.columns(5)
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
            with grid[i % 5]:
                st.markdown(f"**#{card['card_number']} {card['name']}**")
                if card["image_url"]:
                    render_card_image(card["image_url"], dim)
                st.caption(f"{variant} • {str(count).zfill(2)}")
                cols = st.columns(3)
                with cols[0]:
                    if st.button("Info", key=f"info-{card['id']}-{variant}"):
                        st.session_state["open_card"] = {**card, "variant": variant, "count": count}
                with cols[1]:
                    if st.button("-", key=f"rem-{card['id']}-{variant}"):
                        if not remove_instance(engine, user["id"], card["id"], variant):
                            st.warning("Kortet är låst eller saknas.")
                        st.rerun()
                with cols[2]:
                    if st.button("+", key=f"add-{card['id']}-{variant}"):
                        if not add_instance(engine, user["id"], card["id"], variant, "Near Mint"):
                            st.warning("Den varianten finns inte.")
                        st.rerun()

    if st.session_state.get("open_card"):
        card = st.session_state["open_card"]
        with st.dialog(f"{card['name']} • {card['variant']}"):
            if card.get("image_url"):
                st.image(card["image_url"], use_column_width=True)
            st.write(f"Nummer: {card['card_number']}")
            st.write(f"Rarity: {card.get('rarity')}")
            st.write(f"Variant: {card['variant']}")
            st.write(f"Äger: {str(card['count']).zfill(2)}")
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


def main():
    header()

    user = get_current_user()
    if not user:
        login_view()
        return

    with st.sidebar:
        st.write(f"Inloggad: {user['username']}")
        if st.button("Logga ut"):
            logout_user()
            st.rerun()

        pages = ["Samling", "Marknad", "Social Hubb", "Mitt Rum"]
        if require_admin(user):
            pages.append("Admin")
        page = st.radio("Navigering", pages)

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
