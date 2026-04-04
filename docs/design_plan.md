# Design Plan — MYTCGWEB (Streamlit)

## Goals
- Rebuild as Streamlit Cloud app with MySQL/MariaDB backend.
- Full login + security + ownership enforcement.
- Collection-first workflow (sets → cards → variants).
- Social hub and marketplace aligned to original blueprint.
- Room as profile showcase (display stands, shelves, cases).

## Information Architecture
- Sidebar navigation: Samling, Marknad, Social Hubb, Mitt Rum, Admin.
- Login/register gate for all pages.
- Admin used for data import and ops.

## Core Data Model (SQL)
- users
- tcg_sets
- tcg_cards
- card_instances (unique physical items)
- listings
- groups, group_members, group_posts
- room_items

## UX Flow
### Login
- Username + password (bcrypt).
- Session stored in Streamlit session state.

### Collection
- TCG selection grid (logos).
- Sets list/grid with progress (owned/total).
- Set view shows all cards, variants as separate entries.
- Each variant shows counts and +/- controls.

### Market
- List active listings with soft-locked cards.
- Create listing only for verified items.
- Express interest → transaction flow (future).

### Social Hubb
- Group list, join/open.
- Inside group: tabs for Inlägg, Sälj, Köp, Byte, Chatt.
- Posts restricted to verified items for trade/sell/buy.

### Room
- User profile page with display layout.
- Drag/place items on stands/shelves/cases.
- Public view shows only public items.

## Data Ingestion
- Primary source: pokemon.com card pages.
- Fallback: manual admin import.
- Set logos and set symbols loaded from assets folders.

## Security
- All DB queries parameterized.
- Ownership checks on all mutations.
- Soft locks for listings and posts.
- Minimal data exposure (no cross-user edits).

## Deployment
- Streamlit Cloud free plan.
- DB credentials stored in Streamlit secrets.
- `streamlit_app.py` entrypoint.
