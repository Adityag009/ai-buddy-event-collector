from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from extraction.schemas import RawContent


class BaseScraper(ABC):
    """One scraper per source type; operates on a single org row from the CSV."""

    @abstractmethod
    def scrape(self, org: dict[str, Any]) -> list[RawContent]:
        raise NotImplementedError
