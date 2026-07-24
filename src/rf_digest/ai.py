from __future__ import annotations

import json
import os
from datetime import UTC
from typing import Any

import requests

from .models import Article, Digest, DigestItem

ENDPOINT = "https://models.github.ai/inference/chat/completions"

SYSTEM_PROMPT = """You are the editor of a Russian-language professional weekly digest for microwave, RF and antenna engineers.
Select only technically meaningful items. Avoid marketing announcements unless they contain a concrete engineering result.
Use only facts present in the supplied candidates. Never invent performance figures, dates, organizations or conclusions.
Write fluent Russian for an expert audience. Keep standard abbreviations such as RF, СВЧ, ФАР, OMT, NF–FF, MMIC, RFIC, RIS, THz where useful.
Return a single JSON object and no markdown."""


def _candidate_payload(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "source": article.source,
        "published_at": article.published_at.astimezone(UTC).date().isoformat() if article.published_at else None,
        "title": article.title,
        "description": " ".join(article.summary.split())[:600],
        "prefilter_score": round(article.score, 2),
        "matched_keywords": article.matched_keywords[:12],
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model returned no JSON object")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response is not a JSON object")
    return parsed


def create_digest(candidates: list[Article], config: dict[str, Any]) -> Digest:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_MODELS_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_MODELS_TOKEN is required")

    max_items = int(config.get("max_digest_items", 10))
    min_items = int(config.get("min_digest_items", 3))
    model = os.getenv("GITHUB_MODEL", str(config.get("github_model", "openai/gpt-4.1-mini")))
    # Keep the free GitHub Models request compact enough to avoid HTTP 413.
    candidates = candidates[:10]

    user_prompt = {
        "task": (
            f"Select {min_items} to {max_items} strongest items. "
            "Return fields: intro_ru and items. Each item must contain only id, title_ru, summary_ru, "
            "why_it_matters_ru and category. category must be one of: Антенны, СВЧ-компоненты, "
            "Измерения, Спутниковая связь, Радиолокация, Полупроводники, Материалы и производство, "
            "САПР и методы, Наука. summary_ru: 1-2 factual sentences. why_it_matters_ru: 1 concise sentence. "
            "Do not repeat items and do not return URLs. Prefer primary research and concrete specifications."
        ),
        "candidates": [_candidate_payload(a) for a in candidates],
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0.15,
        "max_tokens": 2600,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    edited = _extract_json(content)

    by_id = {a.id: a for a in candidates}
    digest_items: list[DigestItem] = []
    used: set[str] = set()
    for raw in edited.get("items", []):
        if not isinstance(raw, dict):
            continue
        article_id = str(raw.get("id", ""))
        if article_id not in by_id or article_id in used:
            continue
        title_ru = str(raw.get("title_ru", "")).strip()[:300]
        summary_ru = str(raw.get("summary_ru", "")).strip()[:1200]
        why = str(raw.get("why_it_matters_ru", "")).strip()[:700]
        category = str(raw.get("category", "Наука")).strip()[:80]
        if not title_ru or not summary_ru or not why:
            continue
        used.add(article_id)
        digest_items.append(
            DigestItem(
                article=by_id[article_id],
                title_ru=title_ru,
                summary_ru=summary_ru,
                why_it_matters_ru=why,
                category=category,
            )
        )
        if len(digest_items) >= max_items:
            break

    if len(digest_items) < min_items:
        raise RuntimeError(f"Editor selected only {len(digest_items)} valid items; minimum is {min_items}")

    intro = str(edited.get("intro_ru", "Главные новости СВЧ, антенной техники и радиосистем за неделю.")).strip()
    return Digest(intro_ru=intro[:800], items=digest_items)
