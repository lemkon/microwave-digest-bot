from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Article:
    id: str
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime | None
    score: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DigestItem:
    article: Article
    title_ru: str
    summary_ru: str
    why_it_matters_ru: str
    category: str


@dataclass(slots=True)
class Digest:
    intro_ru: str
    items: list[DigestItem]
