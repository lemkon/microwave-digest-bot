from datetime import UTC, date, datetime

from rf_digest.models import Article, Digest, DigestItem
from rf_digest.render import render_telegram_messages


def test_render_escapes_html_and_keeps_source_link():
    article = Article(
        "1",
        "Original",
        "Summary",
        "https://example.com/a",
        "Source",
        datetime.now(UTC),
    )
    digest = Digest(
        "Вводный <текст>",
        [DigestItem(article, "Антенна <X>", "Результат", "Полезно", "Антенны")],
    )
    messages = render_telegram_messages(digest, date(2026, 7, 24))
    assert "&lt;X&gt;" in messages[1]
    assert "https://example.com/a" in messages[1]
    assert all(len(message) <= 4096 for message in messages)
