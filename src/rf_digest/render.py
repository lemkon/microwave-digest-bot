from __future__ import annotations

import html
from datetime import date

from .models import Digest, DigestItem

CATEGORY_EMOJI = {
    "Антенны": "📡",
    "СВЧ-компоненты": "〰️",
    "Измерения": "🔬",
    "Спутниковая связь": "🛰",
    "Радиолокация": "📶",
    "Полупроводники": "🧩",
    "Материалы и производство": "🏭",
    "САПР и методы": "🖥",
    "Наука": "🧪",
}


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def render_telegram_messages(digest: Digest, issue_date: date) -> list[str]:
    header = (
        f"<b>СВЧ-дайджест — {issue_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"{_escape(digest.intro_ru)}\n\n"
        f"В выпуске: {len(digest.items)} материалов."
    )
    messages = [header]
    for index, item in enumerate(digest.items, start=1):
        emoji = CATEGORY_EMOJI.get(item.category, "▪️")
        published = item.article.published_at.date().isoformat() if item.article.published_at else "дата не указана"
        message = (
            f"{emoji} <b>{index}. {_escape(item.title_ru)}</b>\n"
            f"<i>{_escape(item.category)} · {_escape(item.article.source)} · {published}</i>\n\n"
            f"{_escape(item.summary_ru)}\n\n"
            f"<b>Почему это важно:</b> {_escape(item.why_it_matters_ru)}\n\n"
            f"<a href=\"{_escape(item.article.url)}\">Первоисточник</a>"
        )
        if len(message) > 3900:
            message = message[:3850] + "…"
        messages.append(message)
    messages.append("#СВЧ #антенны #радиотехника #microwave #RF")
    return messages


def render_markdown(digest: Digest, issue_date: date) -> str:
    lines = [f"# СВЧ-дайджест — {issue_date.strftime('%d.%m.%Y')}", "", digest.intro_ru, ""]
    for index, item in enumerate(digest.items, start=1):
        lines.extend(
            [
                f"## {index}. {item.title_ru}",
                "",
                f"**Категория:** {item.category}  ",
                f"**Источник:** {item.article.source}  ",
                f"**Оригинал:** {item.article.url}",
                "",
                item.summary_ru,
                "",
                f"**Почему это важно:** {item.why_it_matters_ru}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"
