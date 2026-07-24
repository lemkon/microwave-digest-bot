from __future__ import annotations

import re
from collections.abc import Iterable

from rapidfuzz.fuzz import ratio

from .models import Article

WORD_RE = re.compile(r"[a-zA-Zа-яА-Я0-9+\-/]+")


def _normalise_title(title: str) -> str:
    return " ".join(WORD_RE.findall(title.lower()))


def score_article(article: Article, keyword_weights: dict[str, float], negative_weights: dict[str, float]) -> Article:
    haystack_title = article.title.lower()
    haystack = f"{article.title} {article.summary}".lower()
    score = 0.0
    matched: list[str] = []

    for keyword, weight in keyword_weights.items():
        key = keyword.lower()
        if key in haystack:
            score += float(weight)
            if key in haystack_title:
                score += max(0.5, float(weight) * 0.45)
            matched.append(keyword)

    for keyword, penalty in negative_weights.items():
        if keyword.lower() in haystack:
            score -= abs(float(penalty))

    if article.source.lower() == "arxiv":
        score += 1.0
    if len(article.summary) > 250:
        score += 0.5

    article.score = score
    article.matched_keywords = sorted(set(matched))
    return article


def deduplicate(articles: Iterable[Article], threshold: int = 91) -> list[Article]:
    by_url: dict[str, Article] = {}
    for article in sorted(articles, key=lambda x: x.score, reverse=True):
        by_url.setdefault(article.url, article)

    result: list[Article] = []
    normalised_titles: list[str] = []
    for article in by_url.values():
        title = _normalise_title(article.title)
        if any(ratio(title, existing) >= threshold for existing in normalised_titles):
            continue
        result.append(article)
        normalised_titles.append(title)
    return result


def rank_candidates(articles: list[Article], config: dict, seen_ids: set[str]) -> list[Article]:
    weights = {str(k): float(v) for k, v in config.get("keyword_weights", {}).items()}
    negatives = {str(k): float(v) for k, v in config.get("negative_weights", {}).items()}
    min_score = float(config.get("minimum_prefilter_score", 2.0))
    max_candidates = int(config.get("max_candidates_for_editor", 28))

    scored = [score_article(a, weights, negatives) for a in articles if a.id not in seen_ids]
    scored = [a for a in scored if a.score >= min_score]
    scored = deduplicate(scored)
    scored.sort(key=lambda a: (a.score, a.published_at is not None, a.published_at), reverse=True)
    return scored[:max_candidates]
