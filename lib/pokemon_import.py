import requests
from bs4 import BeautifulSoup


def fetch_pokemon_card(set_code: str, card_number: str):
    url = f"https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/series/{set_code}/{card_number}/"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("meta", {"property": "og:title"})
        image = soup.find("meta", {"property": "og:image"})
        name = title["content"] if title else None
        image_url = image["content"] if image else None
        rarity = None
        rarity_tag = soup.find(string=lambda text: text and "Rarity" in text)
        if rarity_tag:
            parent = rarity_tag.parent
            if parent:
                rarity = parent.get_text(strip=True).replace("Rarity", "").strip()
        return {
            "name": name,
            "image_url": image_url,
            "rarity": rarity,
        }
    except Exception:
        return None
