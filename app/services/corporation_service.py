"""Corporation service for auto-detecting Dhaka North/South Corporation based on thana."""

from __future__ import annotations

from app.models.enums import CorporationType


class CorporationService:
    """Service to auto-detect and manage city corporation assignments."""

    # Map of Dhaka thanas to their city corporation
    THANA_CORPORATION_MAP: dict[str, CorporationType] = {
        # Dhaka North City Corporation (DNCC) Thanas
        "Mirpur": CorporationType.dncc,
        "Dhanmondi": CorporationType.dncc,
        "Gulshan": CorporationType.dncc,
        "Badda": CorporationType.dncc,
        "Banani": CorporationType.dncc,
        "Khilgaon": CorporationType.dncc,
        "Pallabi": CorporationType.dncc,
        "Tejgaon": CorporationType.dncc,
        "Uttara": CorporationType.dncc,
        "Wari": CorporationType.dncc,
        "Mohammadpur": CorporationType.dncc,
        "Adabor": CorporationType.dncc,
        "Kafrul": CorporationType.dncc,
        # Dhaka South City Corporation (DSCC) Thanas
        "Kotwali": CorporationType.dscc,
        "Ramna": CorporationType.dscc,
        "Jatrabari": CorporationType.dscc,
        "Motijheel": CorporationType.dscc,
        "Purana Paltan": CorporationType.dscc,
        "Kamranjung": CorporationType.dscc,
        "Bangla Motor": CorporationType.dscc,
        "Kafrul Bazar": CorporationType.dscc,
        "Basundhara": CorporationType.dscc,
        "South Keraniganj": CorporationType.dscc,
    }

    def get_corporation_by_thana(self, thana: str) -> CorporationType:
        """
        Auto-detect which city corporation a thana belongs to.

        Args:
            thana: Thana name (case-insensitive)

        Returns:
            CorporationType (DNCC or DSCC), defaults to DNCC if not found

        Example:
            >>> service = CorporationService()
            >>> service.get_corporation_by_thana("Mirpur")
            <CorporationType.dncc: 'DNCC'>
        """
        normalized_thana = thana.strip().title()
        return self.THANA_CORPORATION_MAP.get(normalized_thana, CorporationType.dncc)

    def is_dncc(self, thana: str) -> bool:
        """Check if thana belongs to DNCC."""
        return self.get_corporation_by_thana(thana) == CorporationType.dncc

    def is_dscc(self, thana: str) -> bool:
        """Check if thana belongs to DSCC."""
        return self.get_corporation_by_thana(thana) == CorporationType.dscc

    def get_all_dncc_thanas(self) -> list[str]:
        """Get list of all DNCC thanas."""
        return [thana for thana, corp in self.THANA_CORPORATION_MAP.items() if corp == CorporationType.dncc]

    def get_all_dscc_thanas(self) -> list[str]:
        """Get list of all DSCC thanas."""
        return [thana for thana, corp in self.THANA_CORPORATION_MAP.items() if corp == CorporationType.dscc]

    def get_all_thanas(self) -> list[str]:
        """Get list of all known thanas."""
        return list(self.THANA_CORPORATION_MAP.keys())


# Singleton instance
_corporation_service: CorporationService | None = None


def get_corporation_service() -> CorporationService:
    """Get or create corporation service singleton."""
    global _corporation_service
    if _corporation_service is None:
        _corporation_service = CorporationService()
    return _corporation_service
