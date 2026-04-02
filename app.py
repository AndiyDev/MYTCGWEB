import streamlit as st
import json

# Load TCG data
def load_data(game):
    with open(f"data/{game.lower()}.json", "r") as f:
        return json.load(f)

# Sidebar for quick filters
with st.sidebar:
    st.header("Quick Filters")
    game = st.radio(
        "Select a TCG:",
        ("Pokémon", "Magic: The Gathering", "Yu-Gi-Oh!", "One Piece", "Lorcan", "Flesh and Blood")
    )

# Main view for selected TCG
if game == "Pokémon":
    st.header("Pokémon Sets")
    pokemon_sets = load_data("pokemon")

    cols = st.columns(2)
    for i, set in enumerate(pokemon_sets):
        with cols[i % 2]:
            st.image(f"images/{set['image']}", width=150)
            st.write(f"**Progress:** {set['progress']}")
            st.write(f"**Total Value:** {set['value']}")