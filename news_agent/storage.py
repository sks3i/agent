"""Simple SQLite-backed history tracker for deduplication."""
import sqlite3
from datetime import datetime
from pathlib import Path
from hashlib import sha256
from typing import Iterable


class NewsHistory:
    def __init__(self, db_path: str = "news_agent/story_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_stories (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                seen_at TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def _hash(self, url: str) -> str:
        return sha256(url.encode("utf-8")).hexdigest()

    def has_seen(self, urls: Iterable[str]) -> Iterable[bool]:
        cursor = self._conn.cursor()
        for url in urls:
            url_hash = self._hash(url)
            cursor.execute("SELECT 1 FROM seen_stories WHERE url_hash = ?", (url_hash,))
            yield cursor.fetchone() is not None

    def mark_seen(self, url: str, title: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO seen_stories (url_hash, url, title, seen_at) VALUES (?, ?, ?, ?)",
            (self._hash(url), url, title, datetime.utcnow()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
