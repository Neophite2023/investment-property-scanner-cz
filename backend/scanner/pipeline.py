from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from .analyzer import build_market_statistics, build_rental_statistics, match_market_stat, score_listing
from .config import Settings
from .models import Listing
from .sreality import SrealityClient, merge_detail, normalize_many
from .supabase import SupabaseRest


class ScannerPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = SupabaseRest(settings)
        self.sreality = SrealityClient(settings)

    def close(self) -> None:
        self.sreality.close()
        self.db.close()

    def scrape(self, transaction_type: str = "sale", with_detail: bool = True) -> list[Listing]:
        all_listings: list[Listing] = []
        for city in self.settings.cities:
            items = self.sreality.fetch_search(transaction_type, city)
            listings = normalize_many(items, transaction_type, city)
            if with_detail:
                for listing in listings:
                    detail = self.sreality.fetch_detail(listing)
                    if detail:
                        merge_detail(listing, detail)
            all_listings.extend(listings)

        self.persist_listings(all_listings)
        return all_listings

    def persist_listings(self, listings: list[Listing]) -> None:
        rows = [listing.to_db() for listing in listings]
        self.db.upsert("listings", rows, conflict="listing_id")

        now = datetime.now(timezone.utc).isoformat()
        snapshots = []
        price_history = []
        for listing in listings:
            raw_json = json.dumps(listing.raw_data, ensure_ascii=False, sort_keys=True)
            snapshots.append(
                {
                    "listing_id": listing.listing_id,
                    "raw_data": listing.raw_data,
                    "price": listing.price,
                    "title": listing.title,
                    "description": listing.description,
                    "content_hash": hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
                    "captured_at": now,
                }
            )
            if listing.price:
                price_history.append(
                    {
                        "listing_id": listing.listing_id,
                        "price": listing.price,
                        "captured_at": now,
                    }
                )
        self.db.insert("listing_snapshots", snapshots)
        self.db.insert("price_history", price_history)

    def rebuild_market_statistics(self) -> list[dict[str, Any]]:
        rows = self.db.select(
            "listings",
            {
                "select": "listing_id,transaction_type,city,district,layout,price_per_m2,active",
                "active": "eq.true",
            },
        )
        stats = build_market_statistics(rows)
        self.db.upsert("market_statistics", stats, conflict="city,district,layout,transaction_type")
        return stats

    def rebuild_rental_statistics(self) -> list[dict[str, Any]]:
        rows = self.db.select(
            "listings",
            {
                "select": "listing_id,transaction_type,city,district,layout,price,area,active",
                "transaction_type": "eq.rent",
                "active": "eq.true",
            },
        )
        stats = build_rental_statistics(rows)
        self.db.upsert("rental_statistics", stats, conflict="city,district,layout")
        return stats

    def score_active_listings(self) -> list[dict[str, Any]]:
        listings = self.db.select(
            "listings",
            {
                "select": "*",
                "transaction_type": "eq.sale",
                "active": "eq.true",
            },
        )
        market_stats = self.db.select("market_statistics", {"select": "*"})
        rental_stats = self.db.select("rental_statistics", {"select": "*"})
        scores = []
        for listing in listings:
            market_stat = match_market_stat(listing, market_stats)
            rent_stat = match_rent_stat(listing, rental_stats)
            scores.append(score_listing(listing, market_stat, rent_stat).to_db())

        self.db.upsert("scores", scores, conflict="listing_id")
        return scores

    def generate_daily_report(self) -> dict[str, Any]:
        today = date.today().isoformat()
        top_scores = self.db.select(
            "scores",
            {
                "select": "*,listings(*)",
                "order": "investment_score.desc",
                "limit": "10",
            },
        )
        new_listings = self.db.select(
            "listings",
            {
                "select": "listing_id",
                "first_seen": f"gte.{today}",
            },
        )
        price_drops = self.db.rpc("count_price_drops_today", {"target_date": today})
        report_json = {
            "date": today,
            "top_opportunities": top_scores,
            "new_listings_count": len(new_listings),
            "price_drop_count": int(price_drops or 0),
        }
        row = {
            "report_date": today,
            "new_listings_count": len(new_listings),
            "price_drop_count": int(price_drops or 0),
            "report_json": report_json,
        }
        self.db.upsert("reports", row, conflict="report_date")
        return report_json

    def backfill_details(self) -> int:
        rows = self.db.select(
            "listings",
            {
                "select": "*",
                "transaction_type": "eq.sale",
                "active": "eq.true",
                "description": "is.null",
            },
        )
        if not rows:
            return 0

        self.sreality.fetch_search("sale", self.settings.cities[0])  # init buildId
        updated = 0
        for row in rows:
            listing = Listing.from_db(row)
            detail = self.sreality.fetch_detail(listing)
            if not detail:
                continue
            merge_detail(listing, detail)
            self.db.upsert("listings", [listing.to_db()], conflict="listing_id")
            updated += 1

        return updated

    def run_all(self) -> dict[str, Any]:
        sale_listings = self.scrape("sale", with_detail=True)
        rent_listings = self.scrape("rent", with_detail=False)
        market_stats = self.rebuild_market_statistics()
        rental_stats = self.rebuild_rental_statistics()
        scores = self.score_active_listings()
        report = self.generate_daily_report()
        return {
            "sale_listings": len(sale_listings),
            "rent_listings": len(rent_listings),
            "market_stats": len(market_stats),
            "rental_stats": len(rental_stats),
            "scores": len(scores),
            "report": report,
        }


def match_rent_stat(listing: dict[str, Any], stats: list[dict[str, Any]]) -> dict[str, Any] | None:
    city = listing.get("city")
    district = listing.get("district") or "unknown"
    layout = listing.get("layout")
    for row in stats:
        if row.get("city") == city and row.get("district") == district and row.get("layout") == layout:
            return row
    for row in stats:
        if row.get("city") == city and row.get("layout") == layout:
            return row
    return None
