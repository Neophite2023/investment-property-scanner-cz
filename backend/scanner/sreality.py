from __future__ import annotations

import json
import re
from typing import Any, Iterable

import httpx

from .config import Settings
from .models import Listing


AREA_RE = re.compile(r"(\d+(?:[,.]\d+)?)\s*m")
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
    re.DOTALL,
)

TRANSACTION_SLUG = {"sale": "prodej", "rent": "pronajem"}


class SrealityClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(
            timeout=25,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept-Language": "cs,en;q=0.9",
            },
        )

    def close(self) -> None:
        self.client.close()

    def fetch_search(self, transaction_type: str, city: str) -> list[dict[str, Any]]:
        region_id, region_seo = self.settings.get_region(city)
        trans_slug = TRANSACTION_SLUG[transaction_type]
        estates: list[dict[str, Any]] = []

        for page in range(1, self.settings.max_pages + 1):
            page_suffix = f"?strana={page}" if page > 1 else ""
            url = f"https://www.sreality.cz/hledani/{trans_slug}/byty/{region_seo}{page_suffix}"
            response = self.client.get(url)
            response.raise_for_status()

            page_estates = _parse_estates_from_html(response.text)
            if not page_estates:
                break
            estates.extend(page_estates)

            if len(page_estates) < 22:
                break

        return estates

    def fetch_detail(self, listing_id: str) -> dict[str, Any]:
        return {}


DETAIL_URL_RE = re.compile(r'href="(/detail/[^"]+)"')


def _parse_estates_from_html(html: str) -> list[dict[str, Any]]:
    match = NEXT_DATA_RE.search(html)
    if not match:
        return []
    data = json.loads(match.group(1))
    estates = _find_estates_array(data) or []

    # Extract detail URLs from HTML and attach to estates by listing_id
    detail_urls = DETAIL_URL_RE.findall(html)
    for estate in estates:
        eid = str(estate.get("id", ""))
        for url in detail_urls:
            if url.rstrip("/").endswith("/" + eid):
                estate["_detail_url"] = "https://www.sreality.cz" + url
                break

    return estates


def _find_estates_array(obj: Any) -> list[dict[str, Any]] | None:
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "categoryMainCb" in obj[0] and "id" in obj[0]:
            return obj
        for item in obj:
            result = _find_estates_array(item)
            if result:
                return result
    elif isinstance(obj, dict):
        for value in obj.values():
            result = _find_estates_array(value)
            if result:
                return result
    return None


def normalize_search_item(item: dict[str, Any], transaction_type: str, fallback_city: str) -> Listing:
    listing_id = str(item.get("id"))
    title = clean_text(item.get("name") or "Bez názvu")
    locality = item.get("locality") or {}

    price = _extract_price(item)
    area = _extract_area(item, title)
    layout = _extract_layout(item)
    lat = _parse_float(locality.get("latitude"))
    lon = _parse_float(locality.get("longitude"))
    url = item.get("_detail_url")
    if not url:
        url = _construct_url(locality, layout, listing_id, transaction_type)

    city = locality.get("city") or fallback_city
    district = locality.get("district")
    street = locality.get("street")

    return Listing(
        listing_id=listing_id,
        source="sreality",
        transaction_type=transaction_type,
        title=title,
        url=url,
        city=city,
        district=district,
        street=street,
        price=price,
        area=area,
        price_per_m2=round(price / area, 2) if price and area else None,
        layout=layout,
        latitude=lat,
        longitude=lon,
        raw_data=item,
    )


def merge_detail(listing: Listing, detail: dict[str, Any]) -> Listing:
    listing.raw_data = {"search": listing.raw_data}
    return listing


def normalize_many(items: Iterable[dict[str, Any]], transaction_type: str, city: str) -> list[Listing]:
    return [normalize_search_item(item, transaction_type, city) for item in items]


def _construct_url(locality: dict[str, Any], layout: str | None, listing_id: str, transaction_type: str) -> str:
    import unicodedata, re
    def slugify(text: str) -> str:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().strip()
        text = re.sub(r"[^a-z0-9-]", "-", text)
        return re.sub(r"-+", "-", text).strip("-")

    city = slugify(locality.get("city") or "")
    district = slugify(locality.get("district") or "")
    street = slugify(locality.get("street") or "")
    parts = [p for p in [city, district, street] if p]
    loc_slug = "-".join(parts)
    layout_slug = (layout or "").replace(" ", "")
    trans = "pronajem" if transaction_type == "rent" else "prodej"
    return f"https://www.sreality.cz/detail/{trans}/byt/{layout_slug}/{loc_slug}/{listing_id}"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _extract_price(item: dict[str, Any]) -> int | None:
    raw = item.get("priceCzk")
    if isinstance(raw, (int, float)) and raw > 0:
        return int(raw)
    return None


def _extract_area(item: dict[str, Any], title: str) -> float | None:
    raw = item.get("priceCzkPerSqM")
    price = _extract_price(item)
    if price and raw and isinstance(raw, (int, float)) and raw > 0:
        return round(price / raw, 2)
    match = AREA_RE.search(title)
    if match:
        return _parse_float(match.group(1))
    return None


def _extract_layout(item: dict[str, Any]) -> str | None:
    sub = item.get("categorySubCb") or {}
    name = sub.get("name") if isinstance(sub, dict) else None
    if name and re.match(r"^[1-6]\s*\+\s*(?:kk|1)$", name, re.IGNORECASE):
        return name.replace(" ", "").lower()
    return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
