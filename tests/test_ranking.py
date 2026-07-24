from datetime import UTC, datetime

from rf_digest.models import Article
from rf_digest.ranking import deduplicate, score_article


def article(title: str, url: str) -> Article:
    return Article("id", title, "near-field antenna measurement", url, "test", datetime.now(UTC))


def test_keyword_scoring_rewards_title():
    item = article("New phased array antenna", "https://example.com/1")
    score_article(item, {"antenna": 3, "phased array": 4}, {})
    assert item.score > 7


def test_deduplicate_similar_titles():
    a = article("A New Ka-Band Phased Array Antenna", "https://example.com/a")
    b = article("New Ka Band phased-array antenna", "https://example.com/b")
    a.score = 10
    b.score = 8
    assert len(deduplicate([a, b], threshold=80)) == 1
