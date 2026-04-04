import uuid
import streamlit as st
from lib.db import get_engine
from lib.schema import init_schema
from lib.auth import login_user, register_user, logout_user, get_current_user
from lib.collection import get_sets, get_cards_for_set, get_user_variant_counts, add_instance, remove_instance

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
            user = login_user(engine, username, password)
            if not user:
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


def collection_view(user):
    st.markdown("## Samling")
    game = st.radio("Välj TCG", ["pokemon"], horizontal=True)
    sets = get_sets(engine, game)

    if not sets:
        st.info("Inga set finns ännu. Lägg till set i Admin-sektionen.")
        return

    set_cols = st.columns(4)
    selected_set_id = st.session_state.get("selected_set_id")
    for idx, s in enumerate(sets):
        with set_cols[idx % 4]:
            clicked = st.button(f"{s['set_name']}\n{str(s['total_cards']).zfill(3)}", use_container_width=True)
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
            with grid[i % 5]:
                st.markdown(f"**#{card['card_number']} {card['name']}**")
                if card["image_url"]:
                    st.image(card["image_url"], use_column_width=True)
                st.caption(f"{variant} • {str(count).zfill(2)}")
                cols = st.columns(2)
                with cols[0]:
                    if st.button("-", key=f"rem-{card['id']}-{variant}"):
                        remove_instance(engine, user["id"], card["id"], variant)
                        st.rerun()
                with cols[1]:
                    if st.button("+", key=f"add-{card['id']}-{variant}"):
                        add_instance(engine, user["id"], card["id"], variant, "Near Mint")
                        st.rerun()


def market_view():
    st.markdown("## Marknad")
    st.info("Marknaden byggs nu. Här kommer sälj/köp/byte med soft-lockade kort.")


def groups_view():
    st.markdown("## Social Hubb")
    st.info("Gruppflöde och chatt byggs nu. Vi behåller flödet men gör det redo för Streamlit.")


def room_view():
    st.markdown("## Mitt Rum")
    st.info("Rummet byggs om i Streamlit. Fokus: riktig 3D-känsla och möblering.")


def admin_view():
    st.markdown("## Admin / Import")
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
                    sa.text("""
                        INSERT INTO tcg_sets (id, game, series, set_name, set_code, total_cards, logo_path, symbol_path)
                        VALUES (:id, :g, :s, :n, :c, :t, :l, :sym)
                    """),
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
                    sa.text("""
                        INSERT INTO tcg_cards (id, set_id, card_number, name, rarity, image_url, has_normal, has_holofoil, has_reverse_holo)
                        VALUES (:id, :sid, :num, :name, :rar, :img, :hn, :hh, :hr)
                    """),
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
        page = st.radio("Navigering", ["Samling", "Marknad", "Social Hubb", "Mitt Rum", "Admin"])

    if page == "Samling":
        collection_view(user)
    elif page == "Marknad":
        market_view()
    elif page == "Social Hubb":
        groups_view()
    elif page == "Mitt Rum":
        room_view()
    elif page == "Admin":
        admin_view()


if __name__ == "__main__":
    main()
