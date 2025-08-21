from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import List
from datetime import datetime

from app.config.constants import STORIES_DB_PATH


@dataclass
class Episode:
    """Represents a single episode/chapter of a story."""

    title: str
    content: str
    order: int


class StoryManager:
    """Handle storage of stories and their episodes in SQLite."""

    def __init__(self, db_path: Path | str = STORIES_DB_PATH):
        self.db_path = Path(db_path)
        self._init_db()

    # ------------------------------------------------------------------
    # database helpers
    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    description TEXT,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER NOT NULL,
                    ord INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY(story_id) REFERENCES stories(id)
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    def add_story(self, title: str, author: str, description: str, file_path: Path | str):
        """Add a story and parse the provided markdown text file into episodes."""
        text = Path(file_path).read_text(encoding="utf-8")
        episodes = parse_markdown_episodes(text)

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO stories (title, author, description, created) VALUES (?, ?, ?, ?)",
                (title, author, description, datetime.now()),
            )
            story_id = cur.lastrowid

            for ep in episodes:
                cur.execute(
                    "INSERT INTO episodes (story_id, ord, title, content) VALUES (?, ?, ?, ?)",
                    (story_id, ep.order, ep.title, ep.content),
                )
            conn.commit()
        return story_id


# ----------------------------------------------------------------------
def parse_markdown_episodes(text: str) -> List[Episode]:
    """Parse markdown text into a list of episodes.

    Chapters are identified by lines beginning with a single ``#``. The text
    following each heading becomes the episode content.
    """
    pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    episodes: List[Episode] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        title = match.group(1).strip()
        episodes.append(Episode(title=title, content=content, order=index))
    return episodes

