import pgserver
import psycopg

from .bookmark_types import Bookmark


def _init_pg_server() -> str:
    """
    Initializes the local postgresql server and returns the URI to connect
    :return: the connection URI
    """
    db = pgserver.get_server("cache_data")
    db.psql("CREATE EXTENSION IF NOT EXISTS vector")
    db.psql("CREATE TABLE IF NOT EXISTS link_cache (url TEXT PRIMARY KEY, content TEXT, last_fetched TIMESTAMPTZ, failed BOOLEAN)")
    db.psql("CREATE TABLE IF NOT EXISTS summaries (url TEXT PRIMARY KEY REFERENCES link_cache(url), summary TEXT)")
    db.psql("CREATE TABLE IF NOT EXISTS embeddings (url TEXT PRIMARY KEY REFERENCES link_cache(url), embedding vector(1536))")
    return db.get_uri()

def db_connect() -> psycopg.Connection:
    uri = _init_pg_server()
    return psycopg.connect(uri)

def get_cache_entries(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT url, content FROM link_cache WHERE last_fetched > NOW() - INTERVAL '1 month'"
        )
        entries = {row[0]: row[1] for row in cursor.fetchall()}
    return entries

def write_cache(bookmark: Bookmark, content: str | None, failed: bool, conn: psycopg.Connection) -> None:
    from datetime import datetime

    with conn.cursor() as cursor:
        cursor.execute(
            """INSERT INTO link_cache (url, content, last_fetched, failed) 
               VALUES (%s, %s, NOW(), %s) 
               ON CONFLICT(url) DO UPDATE 
               SET content = %s, last_fetched = NOW(), failed = %s""",
            (bookmark.url, content, failed, content, failed)
        )
        conn.commit()

def get_summaries(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT url, summary FROM summaries")
        entries = {row[0]: row[1] for row in cursor.fetchall()}
    return entries

def write_summary(url: str, summary: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """INSERT INTO summaries (url, summary) 
               VALUES (%s, %s) 
               ON CONFLICT(url) DO UPDATE 
               SET summary = %s""",
            (url, summary, summary)
        )
        conn.commit()