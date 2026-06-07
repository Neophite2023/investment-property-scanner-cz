from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


CITY_REGION_MAP: dict[str, tuple[int, str]] = {
    "Brno": (14, "jihomoravsky-kraj"),
    "Zlín": (9, "zlinsky-kraj"),
    "Olomouc": (13, "olomoucky-kraj"),
    "Praha": (10, "praha"),
    "Ostrava": (12, "moravskoslezsky-kraj"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    watch_cities: str = Field(default="Brno,Zlín", alias="WATCH_CITIES")
    max_price_czk: int | None = Field(default=None, alias="MAX_PRICE_CZK")
    min_area_m2: int | None = Field(default=18, alias="MIN_AREA_M2")
    max_pages: int = Field(default=4, alias="MAX_PAGES")

    push_min_score: int = Field(default=85, alias="PUSH_MIN_SCORE")
    push_min_confidence: int = Field(default=60, alias="PUSH_MIN_CONFIDENCE")
    push_min_market_discount_percent: float = Field(default=-8.0, alias="PUSH_MIN_MARKET_DISCOUNT_PERCENT")

    @property
    def cities(self) -> list[str]:
        return [part.strip() for part in self.watch_cities.split(",") if part.strip()]

    def get_region(self, city: str) -> tuple[int, str]:
        # Case-insensitive lookup with normalized capitalisation
        for known, region in CITY_REGION_MAP.items():
            if known.casefold() == city.casefold():
                return region
        msg = f"Neznáme mesto '{city}'. Podporované: {', '.join(CITY_REGION_MAP)}"
        raise ValueError(msg)


@lru_cache
def get_settings() -> Settings:
    return Settings()

