import re
import statistics
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"


def _fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def _extract_prices(text: str) -> List[float]:
    prices = []
    for m in re.findall(r"(\d+[.,]?\d*)\s*(kr|SEK|EUR|€)", text, flags=re.IGNORECASE):
        value = m[0].replace(".", "").replace(",", ".")
        try:
            prices.append(float(value))
        except Exception:
            continue
    return prices


def _summary(prices: List[float]) -> Tuple[float, float, float]:
    if not prices:
        return 0.0, 0.0, 0.0
    prices = sorted(prices)
    return prices[0], statistics.median(prices), prices[-1]


def scrape_source(source: str, query: str) -> dict:
    source = source.lower()
    if source == "cardmarket":
        url = f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={requests.utils.quote(query)}"
    elif source == "tcgplayer":
        url = f"https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&q={requests.utils.quote(query)}"
    elif source == "tradera":
        url = f"https://www.tradera.com/search?q={requests.utils.quote(query)}"
    elif source == "blocket":
        url = f"https://www.blocket.se/annonser/hela_sverige?q={requests.utils.quote(query)}"
    elif source == "vinted":
        url = f"https://www.vinted.se/catalog?search_text={requests.utils.quote(query)}"
    elif source == "ebay":
        url = f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(query)}"
    else:
        return {"source": source, "error": "unknown_source", "prices": []}

    try:
        html = _fetch(url)
    except Exception as exc:
        return {"source": source, "error": str(exc), "prices": [], "url": url}

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    prices = _extract_prices(text)
    if not prices:
        return {"source": source, "error": "no_prices_found", "prices": [], "url": url}

    low, median, high = _summary(prices)
    return {"source": source, "prices": prices[:50], "low": low, "median": median, "high": high, "url": url}
