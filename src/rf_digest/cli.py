from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from .ai import create_digest
from .config import load_config
from .fetchers import fetch_all
from .ranking import rank_candidates
from .render import render_markdown, render_telegram_messages
from .state import State
from .telegram import send_messages

LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally publish the weekly RF digest")
    parser.add_argument("--config", default="config/sources.yml")
    parser.add_argument("--state", default="data/state.json")
    parser.add_argument("--mode", choices=("preview", "publish"), default="preview")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    state = State(args.state)

    articles = fetch_all(config)
    LOGGER.info("Fetched %d total articles", len(articles))
    candidates = rank_candidates(articles, config, state.seen_ids)
    LOGGER.info("Prepared %d candidates for the editor", len(candidates))

    minimum = int(config.get("min_digest_items", 3))
    if len(candidates) < minimum:
        raise RuntimeError(f"Only {len(candidates)} candidates passed prefilter; need at least {minimum}")

    digest = create_digest(candidates, config)
    now = datetime.now(UTC)
    issue_date = now.date()
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    issue_name = f"digest-{issue_date.isoformat()}.md"
    issue_path = output_dir / issue_name
    markdown = render_markdown(digest, issue_date)
    issue_path.write_text(markdown, encoding="utf-8")
    (output_dir / "latest.md").write_text(markdown, encoding="utf-8")
    (output_dir / "latest.json").write_text(
        json.dumps(
            {
                "date": issue_date.isoformat(),
                "items": [
                    {
                        "id": item.article.id,
                        "title_ru": item.title_ru,
                        "source": item.article.source,
                        "url": item.article.url,
                        "category": item.category,
                    }
                    for item in digest.items
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    messages = render_telegram_messages(digest, issue_date)
    if args.mode == "publish":
        send_messages(messages)
        state.mark_published([item.article.id for item in digest.items], str(issue_path))
        state.save()
        LOGGER.info("Published %d digest items", len(digest.items))
    else:
        print(markdown)
        LOGGER.info("Preview only: Telegram was not called and state was not changed")

    Path("data/last_run.txt").write_text(now.isoformat() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
