import sqlite3
from typing import Tuple, NamedTuple

import numpy as np

from .bookmark_types import Bookmark, GUID

_DB_PATH = "cache.sqlite"

class CacheEntry(NamedTuple):
    content: str
    screenshot: bytes


def _init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS link_cache (url TEXT PRIMARY KEY, content TEXT, screenshot BLOB, last_fetched DATETIME, failed INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS summaries (guid TEXT PRIMARY KEY, url TEXT REFERENCES link_cache(url), summary TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS embeddings (guid TEXT PRIMARY KEY, url TEXT REFERENCES link_cache(url), embedding BLOB)")
    conn.execute("CREATE TABLE IF NOT EXISTS screenshot_summaries (guid TEXT PRIMARY KEY, url TEXT REFERENCES link_cache(url), summary TEXT)")
    conn.commit()
    return conn


def db_connect() -> sqlite3.Connection:
    return _init_db()


def get_cache_entries(conn: sqlite3.Connection) -> dict[str, CacheEntry]:
    cursor = conn.execute(
        "SELECT url, content, screenshot FROM link_cache WHERE last_fetched > datetime('now', '-1 month')"
    )
    return {row[0]: CacheEntry(content=row[1], screenshot=row[2]) for row in cursor.fetchall()}


def write_cache(bookmark: Bookmark, content: str | None, screenshot: bytes | None, failed: bool, conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT INTO link_cache (url, content, screenshot, last_fetched, failed)
           VALUES (?, ?, ?, datetime('now'), ?)
           ON CONFLICT(url) DO UPDATE
           SET content = ?, screenshot = ?, last_fetched = datetime('now'), failed = ?""",
        (bookmark.url, content, screenshot, failed, content, screenshot, failed)
    )
    conn.commit()


def get_summaries(conn: sqlite3.Connection) -> dict[GUID, str]:
    cursor = conn.execute("SELECT guid, summary FROM summaries")
    return {row[0]: row[1] for row in cursor.fetchall()}


def write_summary(guid: GUID, url: str, summary: str, conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT INTO summaries (guid, url, summary)
           VALUES (?, ?, ?)
           ON CONFLICT(guid) DO UPDATE
           SET summary = ?""",
        (guid, url, summary, summary)
    )
    conn.commit()


def get_embeddings(conn: sqlite3.Connection) -> list[Tuple[GUID, np.ndarray]]:
    """
    :param conn:
    :return: List of (guid, embedding vector) tuples for all entries in the embeddings table
    """
    cursor = conn.execute("SELECT guid, embedding FROM embeddings")
    return [(row[0], np.frombuffer(row[1], dtype=np.float64)) for row in cursor.fetchall()]


def get_screenshot_summaries(conn: sqlite3.Connection) -> dict[GUID, str]:
    cursor = conn.execute("SELECT guid, summary FROM screenshot_summaries")
    return {row[0]: row[1] for row in cursor.fetchall()}


def write_screenshot_summary(guid: GUID, url: str, summary: str, conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT INTO screenshot_summaries (guid, url, summary)
           VALUES (?, ?, ?)
           ON CONFLICT(guid) DO UPDATE
           SET summary = ?""",
        (guid, url, summary, summary)
    )
    conn.commit()


def write_embedding(guid: GUID, url: str, embedding: np.ndarray, conn: sqlite3.Connection) -> None:
    blob = embedding.tobytes()
    conn.execute(
        """INSERT INTO embeddings (guid, url, embedding)
           VALUES (?, ?, ?)
           ON CONFLICT(guid) DO UPDATE
           SET embedding = ?""",
        (guid, url, blob, blob)
    )
    conn.commit()
