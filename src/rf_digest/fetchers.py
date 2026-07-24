from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus, urlsplit, urlunsplit

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .models import Article

LOGGER = logging.getLogger(__name__)
USER_AGENT = "rf-digest-bot/0.1 (+https://github.com/)"


def _clean_text(value: str | None, max_chars: int = 1800) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    text = " ".join(text.split())
    return text[:max_chars]


def _canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    clean_path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), clean_path, "", ""))


def _article_id(url: str, title: str) -> str:
    raw = f"{_canonical_url(url)}|{title.strip().lower()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _parse_date(entry: Any) -> datetime | None:
    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                try:
                    dt = date_parser.parse(raw)
                except (TypeError, ValueError, OverflowError):
                    continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    return None


def _fetch_feed(url: str, timeout: int) -> feedparser.FeedParserDict:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
    )
    response.raise_for_status()
    return feedparser.parse(response.content)


def fetch_rss_source(source: dict[str, Any], cutoff: datetime, timeout: int) -> list[Article]:
    name = str(source["name"])
    url = str(source["url"])
    parsed = _fetch_feed(url, timeout)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"Invalid feed from {name}: {parsed.bozo_exception}")

    articles: list[Article] = []
    for entry in parsed.entries:
        link = str(entry.get("link") or "").strip()
        title = _clean_text(entry.get("title"), 400)
        if not link or not title:
            continue
        published = _parse_date(entry)
        if published and published < cutoff:
            continue
        content = entry.get("content") or [{}]
        summary = _clean_text(entry.get("summary") or entry.get("description") or content[0].get("value"))
        articles.append(
            Article(
                id=_article_id(link, title),
                title=title,
                summary=summary,
                url=_canonical_url(link),
                source=name,
                published_at=published,
            )
        )
    return articles


def fetch_arxiv_source(source: dict[str, Any], cutoff: datetime, timeout: int) -> list[Article]:
    name = str(source.get("name", "arXiv"))
    query = str(source["query"])
    max_results = int(source.get("max_results", 100))
    encoded_query = quote_plus(query, safe=':"()')
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query={encoded_query}&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    parsed = _fetch_feed(url, timeout)
    articles: list[Article] = []
    for entry in parsed.entries:
        link = str(entry.get("link") or "").strip()
        title = _clean_text(entry.get("title"), 400)
        if not link or not title:
            continue
        published = _parse_date(entry)
        if published and published < cutoff:
            continue
        summary = _clean_text(entry.get("summary"), 2200)
        authors = ", ".join(a.get("name", "") for a in entry.get("authors", []) if a.get("name"))
        if authors:
            summary = f"Authors: {authors}. {summary}"
        articles.append(
            Article(
                id=_article_id(link, title),
                title=title,
                summary=summary,
                url=_canonical_url(link),
                source=name,
                published_at=published,
            )
        )
    return articles


def fetch_all(config: dict[str, Any]) -> list[Article]:
    days = int(config.get("lookback_days", 8))
    cutoff = datetime.now(UTC) - timedelta(days=days)
    timeout = int(config.get("http_timeout_seconds", 25))
    result: list[Article] = []

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        try:
            source_type = source.get("type", "rss")
            if source_type == "rss":
                items = fetch_rss_source(source, cutoff, timeout)
            elif source_type == "arxiv":
                items = fetch_arxiv_source(source, cutoff, timeout)
            else:
                LOGGER.warning("Unknown source type %s for %s", source_type, source.get("name"))
                continue
            LOGGER.info("Fetched %d items from %s", len(items), source.get("name"))
            result.extend(items)
        except Exception as exc:  # one broken feed must not break the whole issue
            LOGGER.warning("Source %s failed: %s", source.get("name"), exc)
    return result
