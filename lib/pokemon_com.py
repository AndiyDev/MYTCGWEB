import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE = "https://www.pokemon.com"


CARD_URL_RE = re.compile(r"^/us/pokemon-tcg/pokemon-cards/series/[^/]+/[^/]+/?$")


def fetch_set_card_links(expansion_code: str) -> list[str]:
    url = f"{BASE}/us/pokemon-tcg/pokemon-cards?{expansion_code}=on"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if CARD_URL_RE.match(href):
            links.add(urljoin(BASE, href))
    return sorted(links)


def fetch_card_detail(card_url: str) -> dict:
    resp = requests.get(card_url, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    name = og_title["content"].strip() if og_title and og_title.get("content") else None
    image_url = og_image["content"].strip() if og_image and og_image.get("content") else None

    number = None
    number_el = soup.find(string=re.compile(r"^\s*\d+/\d+\s*$"))
    if number_el:
        number = number_el.strip().split("/")[0]
    return {
        "name": name,
        "image_url": image_url,
        "number": number,
    }


def import_set_from_pokemon_com(engine, expansion_code: str, delay: float = 0.4):
    from sqlalchemy import text

    links = fetch_set_card_links(expansion_code)
    if not links:
        return {"imported": 0, "links": 0}

    imported = 0
    with engine.begin() as conn:
        for link in links:
            data = fetch_card_detail(link)
            if not data.get("name") or not data.get("image_url") or not data.get("number"):
                continue
            number = data["number"]
            card_id = f"{expansion_code}-{number.zfill(3) if number.isdigit() else number}"
            conn.execute(
                text(
                    """
                    INSERT INTO tcg_cards (id, set_id, card_number, name, rarity, image_url, has_normal, has_holofoil, has_reverse_holo)
                    VALUES (:id, :set_id, :num, :name, NULL, :img, 1, 0, 0)
                    ON DUPLICATE KEY UPDATE
                        card_number=VALUES(card_number),
                        name=VALUES(name),
                        image_url=VALUES(image_url)
                    """
                ),
                {
                    "id": card_id,
                    "set_id": expansion_code,
                    "num": number,
                    "name": data["name"],
                    "img": data["image_url"],
                },
            )
            imported += 1
            time.sleep(delay)
    return {"imported": imported, "links": len(links)}
