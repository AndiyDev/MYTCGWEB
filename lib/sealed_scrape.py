import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE = "https://tcg.pokemon.com"
URL = "https://tcg.pokemon.com/en-us/expansions/perfect-order/#featured-products"


def scrape_featured_products():
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    products = []

    for card in soup.find_all(["article", "div"], class_=re.compile(r"product|featured", re.I)):
        title = card.get_text(" ", strip=True)
        img = card.find("img")
        img_url = None
        if img and img.get("src"):
            img_url = urljoin(BASE, img["src"])
        if title:
            products.append({"name": title, "image_url": img_url})

    # fallback: any image with product-like alt
    if not products:
        for img in soup.find_all("img"):
            alt = (img.get("alt") or "").strip()
            if alt:
                products.append({"name": alt, "image_url": urljoin(BASE, img.get("src"))})

    # de-dup
    seen = set()
    unique = []
    for p in products:
        key = (p["name"], p.get("image_url"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique
