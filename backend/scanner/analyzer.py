from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any

from .models import Score


POSITIVE_TERMS = {
    "novostavba": 8,
    "rekonstrukce": 6,
    "rekonštrukcia": 6,
    "nové rozvody": 6,
    "balkon": 3,
    "balkón": 3,
    "lodžie": 3,
    "terasa": 4,
    "výtah": 4,
    "parkování": 4,
}

RISK_TERMS = {
    "původní stav": 12,
    "povodny stav": 12,
    "družstevní": 18,
    "druzstevni": 18,
    "nutná rekonstrukce": 18,
    "nutna rekonstrukce": 18,
    "bez výtahu": 10,
    "prizemi": 8,
    "přízemí": 8,
    "podíl na cestě": 15,
    "exekuce": 30,
    "dražba": 22,
}


def build_market_statistics(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[float]] = {}
    for row in listings:
        if row.get("transaction_type") != "sale":
            continue
        ppm = row.get("price_per_m2")
        if not ppm or not row.get("city") or not row.get("layout"):
            continue
        key = (
            row["city"],
            row.get("district") or "unknown",
            row["layout"],
            row.get("transaction_type") or "sale",
        )
        groups.setdefault(key, []).append(float(ppm))

    stats: list[dict[str, Any]] = []
    for (city, district, layout, transaction_type), values in groups.items():
        filtered = trim_outliers(values)
        if not filtered:
            continue
        sorted_values = sorted(filtered)
        stats.append(
            {
                "city": city,
                "district": district,
                "layout": layout,
                "transaction_type": transaction_type,
                "median_price_per_m2": round(statistics.median(sorted_values), 2),
                "average_price_per_m2": round(statistics.mean(sorted_values), 2),
                "p25_price_per_m2": round(percentile(sorted_values, 0.25), 2),
                "p75_price_per_m2": round(percentile(sorted_values, 0.75), 2),
                "sample_size": len(sorted_values),
            }
        )
    return stats


def build_rental_statistics(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[tuple[float, float | None]]] = {}
    for row in listings:
        if row.get("transaction_type") != "rent":
            continue
        rent = row.get("price")
        if not rent or not row.get("city") or not row.get("layout"):
            continue
        key = (row["city"], row.get("district") or "unknown", row["layout"])
        groups.setdefault(key, []).append((float(rent), row.get("area")))

    stats: list[dict[str, Any]] = []
    for (city, district, layout), values in groups.items():
        rents = trim_outliers([value[0] for value in values])
        rent_per_m2 = [
            rent / float(area)
            for rent, area in values
            if area and float(area) > 0 and rent in rents
        ]
        if not rents:
            continue
        stats.append(
            {
                "city": city,
                "district": district,
                "layout": layout,
                "average_rent": round(statistics.mean(rents)),
                "median_rent": round(statistics.median(rents)),
                "average_rent_per_m2": round(statistics.mean(rent_per_m2), 2) if rent_per_m2 else None,
                "sample_size": len(rents),
            }
        )
    return stats


def score_listing(listing: dict[str, Any], market_stat: dict[str, Any] | None, rent_stat: dict[str, Any] | None = None) -> Score:
    market_difference = None
    price_score = 40
    reasons: list[str] = []
    risks: list[str] = []

    if market_stat and listing.get("price_per_m2") and market_stat.get("median_price_per_m2"):
        market_difference = ((float(listing["price_per_m2"]) / float(market_stat["median_price_per_m2"])) - 1) * 100
        price_score = clamp(round(50 - market_difference * 2.2), 0, 100)
        if market_difference <= -8:
            reasons.append(f"Cena je {abs(market_difference):.1f} % pod lokálnym mediánom.")
        elif market_difference > 8:
            risks.append(f"Cena je {market_difference:.1f} % nad lokálnym mediánom.")
    else:
        risks.append("Chýba dostatočný lokálny cenový index.")

    estimated_rent = rent_stat.get("average_rent") if rent_stat else None
    gross_yield = None
    yield_score = 45
    if estimated_rent and listing.get("price"):
        gross_yield = (float(estimated_rent) * 12 / float(listing["price"])) * 100
        yield_score = clamp(round((gross_yield - 2.5) * 28), 0, 100)
        if gross_yield >= 4.8:
            reasons.append(f"Odhadovaný hrubý výnos je {gross_yield:.2f} %.")
    else:
        risks.append("Zatiaľ chýba odhad nájmu pre túto kombináciu lokality a dispozície.")

    text = " ".join(
        str(listing.get(key) or "")
        for key in ("title", "description", "condition", "ownership")
    ).lower()
    condition_bonus = sum(points for term, points in POSITIVE_TERMS.items() if term in text)
    risk_penalty = sum(points for term, points in RISK_TERMS.items() if term in text)
    for term in RISK_TERMS:
        if term in text:
            risks.append(f"Rizikový indikátor v texte: {term}.")

    condition_score = clamp(55 + condition_bonus - risk_penalty, 0, 100)
    liquidity_score = liquidity_from_layout(listing.get("layout"))
    location_score = 65 if listing.get("district") else 45

    base = (
        price_score * 0.30
        + yield_score * 0.25
        + liquidity_score * 0.15
        + location_score * 0.10
        + condition_score * 0.10
        + 50 * 0.10
    )

    age_modifier, age_reason, age_risk = _age_score(listing.get("first_seen"))
    if age_reason:
        reasons.append(age_reason)
    if age_risk:
        risks.append(age_risk)

    investment_score = clamp(round(base - min(risk_penalty, 30) + age_modifier), 0, 100)
    confidence = confidence_score(market_stat, rent_stat, listing)

    deal_type = "Na preverenie"
    next_action = "Skontrolovať detail a porovnať s podobnými bytmi."
    if investment_score >= 85 and confidence >= 60 and not has_critical_risk(risks):
        deal_type = "Silná investičná príležitosť"
        next_action = "Kontaktovať makléra do 24 hodín."
    elif market_difference is not None and market_difference <= -8:
        deal_type = "Cena pod trhom"
        next_action = "Overiť právny stav, technický stav a dôvod nižšej ceny."

    return Score(
        listing_id=listing["listing_id"],
        investment_score=investment_score,
        confidence_score=confidence,
        yield_score=yield_score,
        price_score=price_score,
        location_score=location_score,
        condition_score=condition_score,
        liquidity_score=liquidity_score,
        risk_penalty=risk_penalty,
        estimated_rent=int(estimated_rent) if estimated_rent else None,
        estimated_gross_yield=round(gross_yield, 2) if gross_yield else None,
        market_difference_percent=round(market_difference, 2) if market_difference is not None else None,
        deal_type=deal_type,
        reasons=reasons,
        risks=risks,
        next_action=next_action,
    )


def match_market_stat(listing: dict[str, Any], stats: list[dict[str, Any]]) -> dict[str, Any] | None:
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


def confidence_score(market_stat: dict[str, Any] | None, rent_stat: dict[str, Any] | None, listing: dict[str, Any]) -> int:
    score = 30
    sample_size = int(market_stat.get("sample_size") or 0) if market_stat else 0
    rent_sample_size = int(rent_stat.get("sample_size") or 0) if rent_stat else 0
    score += min(sample_size * 4, 35)
    score += min(rent_sample_size * 3, 20)
    if listing.get("area") and listing.get("price") and listing.get("layout"):
        score += 10
    if listing.get("district"):
        score += 5
    return clamp(score, 0, 100)


def liquidity_from_layout(layout: str | None) -> int:
    if layout in {"1+kk", "1+1", "2+kk", "2+1"}:
        return 85
    if layout in {"3+kk", "3+1"}:
        return 70
    return 50


def trim_outliers(values: list[float]) -> list[float]:
    if len(values) < 5:
        return values
    sorted_values = sorted(values)
    p25 = percentile(sorted_values, 0.25)
    p75 = percentile(sorted_values, 0.75)
    iqr = p75 - p25
    lower = p25 - 1.5 * iqr
    upper = p75 + 1.5 * iqr
    return [value for value in sorted_values if lower <= value <= upper]


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0
    index = (len(sorted_values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def has_critical_risk(risks: list[str]) -> bool:
    critical_terms = ("družstevní", "druzstevni", "exekuce", "dražba", "podíl")
    joined = " ".join(risks).lower()
    return any(term in joined for term in critical_terms)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _age_score(first_seen: str | None) -> tuple[int, str | None, str | None]:
    if not first_seen:
        return 0, None, None

    try:
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(first_seen)).days
        if days < 0:
            return 0, None, None
    except (ValueError, TypeError):
        return 0, None, None

    if days <= 3:
        if days == 0:
            modifier = 0
            reason = "Čerstvá ponuka — objavená dnes."
        elif days == 1:
            modifier = 0
            reason = "Čerstvá ponuka — objavená včera."
        else:
            modifier = 0
            reason = f"Čerstvá ponuka — objavená pred {days} dňami."
        risk = None
    elif days <= 14:
        modifier = 3
        reason = f"Inzerát na trhu {days} dní — predajca môže byť ústretovejší k vyjednávaniu."
        risk = None
    elif days <= 30:
        modifier = 5
        reason = f"Inzerát na trhu {days} dní — predajca pravdepodobne otvorený vyjednávaniu."
        risk = None
    elif days <= 60:
        modifier = 3
        reason = f"Inzerát na trhu {days} dní — väčší priestor na vyjednávanie."
        risk = f"Na trhu už {days} dní — overiť, či s nehnuteľnosťou nie je skrytý problém."
    elif days <= 90:
        modifier = 0
        reason = f"Inzerát na trhu {days} dní — vysoká vyjednávacia páka."
        risk = f"Na trhu už {days} dní — riziko skrytého problému."
    else:
        modifier = -5
        reason = None
        risk = f"Na trhu už {days} dní — pravdepodobne vážny dôvod nepredajnosti."

    return modifier, reason, risk
