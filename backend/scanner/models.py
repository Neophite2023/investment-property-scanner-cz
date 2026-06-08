from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Listing:
    listing_id: str
    source: str
    transaction_type: str
    title: str
    url: str
    city: str | None = None
    district: str | None = None
    street: str | None = None
    price: int | None = None
    area: float | None = None
    price_per_m2: float | None = None
    layout: str | None = None
    ownership: str | None = None
    floor: int | None = None
    floors_total: int | None = None
    condition: str | None = None
    elevator: bool | None = None
    balcony: bool | None = None
    terrace: bool | None = None
    cellar: bool | None = None
    parking: bool | None = None
    garage: bool | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    active: bool = True
    first_seen: str | None = None
    last_seen: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_db(cls, row: dict[str, Any]) -> Listing:
        return cls(
            listing_id=row.get("listing_id") or "",
            source=row.get("source") or "",
            transaction_type=row.get("transaction_type") or "",
            title=row.get("title") or "",
            url=row.get("url") or "",
            city=row.get("city"),
            district=row.get("district"),
            street=row.get("street"),
            price=row.get("price"),
            area=row.get("area"),
            price_per_m2=row.get("price_per_m2"),
            layout=row.get("layout"),
            ownership=row.get("ownership"),
            floor=row.get("floor"),
            floors_total=row.get("floors_total"),
            condition=row.get("condition"),
            elevator=row.get("elevator"),
            balcony=row.get("balcony"),
            terrace=row.get("terrace"),
            cellar=row.get("cellar"),
            parking=row.get("parking"),
            garage=row.get("garage"),
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
            description=row.get("description"),
            active=row.get("active", True),
            first_seen=row.get("first_seen"),
            last_seen=row.get("last_seen"),
            raw_data=row.get("raw_data") or {},
        )

    def to_db(self) -> dict[str, Any]:
        now = utcnow().isoformat()
        return {
            "listing_id": self.listing_id,
            "source": self.source,
            "transaction_type": self.transaction_type,
            "title": self.title,
            "url": self.url,
            "city": self.city,
            "district": self.district,
            "street": self.street,
            "price": self.price,
            "area": self.area,
            "price_per_m2": self.price_per_m2,
            "layout": self.layout,
            "ownership": self.ownership,
            "floor": self.floor,
            "floors_total": self.floors_total,
            "condition": self.condition,
            "elevator": self.elevator,
            "balcony": self.balcony,
            "terrace": self.terrace,
            "cellar": self.cellar,
            "parking": self.parking,
            "garage": self.garage,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "description": self.description,
            "active": self.active,
            "first_seen": self.first_seen or now,
            "last_seen": now,
            "updated_at": now,
        }


@dataclass(slots=True)
class Score:
    listing_id: str
    investment_score: int
    confidence_score: int
    yield_score: int
    price_score: int
    location_score: int
    condition_score: int
    liquidity_score: int
    risk_penalty: int
    estimated_rent: int | None
    estimated_gross_yield: float | None
    market_difference_percent: float | None
    deal_type: str
    reasons: list[str]
    risks: list[str]
    next_action: str

    def to_db(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "investment_score": self.investment_score,
            "confidence_score": self.confidence_score,
            "yield_score": self.yield_score,
            "price_score": self.price_score,
            "location_score": self.location_score,
            "condition_score": self.condition_score,
            "liquidity_score": self.liquidity_score,
            "risk_penalty": self.risk_penalty,
            "estimated_rent": self.estimated_rent,
            "estimated_gross_yield": self.estimated_gross_yield,
            "market_difference_percent": self.market_difference_percent,
            "deal_type": self.deal_type,
            "reasons": self.reasons,
            "risks": self.risks,
            "next_action": self.next_action,
        }

