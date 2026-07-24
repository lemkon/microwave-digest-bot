from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class State:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = {"seen_ids": [], "issues": []}
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)

    @property
    def seen_ids(self) -> set[str]:
        return set(str(x) for x in self.data.get("seen_ids", []))

    def mark_published(self, ids: list[str], issue_file: str) -> None:
        seen = list(dict.fromkeys([*self.data.get("seen_ids", []), *ids]))
        self.data["seen_ids"] = seen[-3000:]
        issues = list(self.data.get("issues", []))
        issues.append(
            {
                "published_at": datetime.now(UTC).isoformat(),
                "article_ids": ids,
                "issue_file": issue_file,
            }
        )
        self.data["issues"] = issues[-100:]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
