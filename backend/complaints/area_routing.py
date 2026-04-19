"""Ward-based routing helpers for Dhaka city corporation complaints."""

from __future__ import annotations


CITY_CORPORATION_DNCC = "DNCC"
CITY_CORPORATION_DSCC = "DSCC"

CITY_CORPORATION_CHOICES = [
    (CITY_CORPORATION_DNCC, "Dhaka North City Corporation (DNCC)"),
    (CITY_CORPORATION_DSCC, "Dhaka South City Corporation (DSCC)"),
]

WARD_NUMBER_CHOICES = [(number, f"Ward {number}") for number in range(1, 76)]


def normalize_text(value: str | None) -> str:
    """Normalize free-text area values for safe comparison."""
    return (value or "").strip().casefold()


def normalize_city_corporation(value: str | None) -> str:
    """Normalize a city corporation code."""
    return (value or "").strip().upper()


def same_service_area(
    *,
    left_city_corporation: str | None,
    left_ward_number: int | None,
    left_thana: str | None = "",
    right_city_corporation: str | None,
    right_ward_number: int | None,
    right_thana: str | None = "",
) -> bool:
    """Return whether two coverage definitions refer to the same service area."""
    left_city = normalize_city_corporation(left_city_corporation)
    right_city = normalize_city_corporation(right_city_corporation)

    if left_city and right_city and left_ward_number and right_ward_number:
        return left_city == right_city and int(left_ward_number) == int(right_ward_number)

    return normalize_text(left_thana) == normalize_text(right_thana)


def service_area_label(city_corporation: str | None, ward_number: int | None, thana: str | None = "") -> str:
    """Build a human-readable label for a complaint or authority coverage area."""
    parts: list[str] = []
    city = normalize_city_corporation(city_corporation)
    if city:
        parts.append(city)
    if ward_number:
        parts.append(f"Ward {ward_number}")
    if normalize_text(thana):
        parts.append((thana or "").strip())
    return " | ".join(parts)
