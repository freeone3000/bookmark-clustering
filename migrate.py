"""One-time migrations for the bookmark-cluster cache database."""
import logging
import sqlite3

import numpy as np
from src.bookmarks_cluster.bookmark_types import GUID


_DB_PATH = "cache.sqlite"


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _get_url_to_guid() -> dict[str, GUID]:
    """Build a url→guid mapping from the Firefox places database."""
    from src.bookmarks_cluster.firefox.ff_loader import _get_profile_path
    import os

    base_path = _get_profile_path()
    profile_path = None
    for entry in os.listdir(base_path):
        if entry.endswith(".default-release"):
            profile_path = os.path.join(base_path, entry)
            break
    if profile_path is None:
        raise FileNotFoundError("Could not find Firefox profile directory.")

    places_db = os.path.join(profile_path, "places.sqlite")
    conn = sqlite3.connect(f"file:{places_db}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT url, b.guid FROM moz_bookmarks AS b "
            "JOIN moz_places ON b.fk = moz_places.id "
            "WHERE b.fk IS NOT NULL"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


def migrate_add_guid_if_needed():
    """Add guid column to summaries and embeddings tables, backfilling from Firefox places."""
    conn = sqlite3.connect(_DB_PATH)

    needs_summaries = not _has_column(conn, "summaries", "guid")
    needs_embeddings = not _has_column(conn, "embeddings", "guid")

    if not needs_summaries and not needs_embeddings:
        print("No guid migration needed.")
        conn.close()
        return

    url_to_guid = _get_url_to_guid()

    if needs_summaries:
        print("Migrating summaries table to use guid...")
        conn.execute("ALTER TABLE summaries ADD COLUMN guid TEXT")
        cursor = conn.execute("SELECT url FROM summaries")
        for (url,) in cursor.fetchall():
            guid = url_to_guid.get(url)
            if guid:
                conn.execute("UPDATE summaries SET guid = ? WHERE url = ?", (guid, url))
            else:
                print(f"  Warning: no guid found for url {url}, removing row")
                conn.execute("DELETE FROM summaries WHERE url = ?", (url,))
        conn.commit()

        # Rebuild table with guid as primary key
        conn.execute("CREATE TABLE summaries_new (guid TEXT PRIMARY KEY, url TEXT REFERENCES link_cache(url), summary TEXT)")
        conn.execute("INSERT INTO summaries_new (guid, url, summary) SELECT guid, url, summary FROM summaries WHERE guid IS NOT NULL")
        conn.execute("DROP TABLE summaries")
        conn.execute("ALTER TABLE summaries_new RENAME TO summaries")
        conn.commit()
        print(f"  Migrated summaries table.")

    if needs_embeddings:
        print("Migrating embeddings table to use guid...")
        conn.execute("ALTER TABLE embeddings ADD COLUMN guid TEXT")
        cursor = conn.execute("SELECT url FROM embeddings")
        for (url,) in cursor.fetchall():
            guid = url_to_guid.get(url)
            if guid:
                conn.execute("UPDATE embeddings SET guid = ? WHERE url = ?", (guid, url))
            else:
                print(f"  Warning: no guid found for url {url}, removing row")
                conn.execute("DELETE FROM embeddings WHERE url = ?", (url,))
        conn.commit()

        # Rebuild table with guid as primary key
        conn.execute("CREATE TABLE embeddings_new (guid TEXT PRIMARY KEY, url TEXT REFERENCES link_cache(url), embedding BLOB)")
        conn.execute("INSERT INTO embeddings_new (guid, url, embedding) SELECT guid, url, embedding FROM embeddings WHERE guid IS NOT NULL")
        conn.execute("DROP TABLE embeddings")
        conn.execute("ALTER TABLE embeddings_new RENAME TO embeddings")
        conn.commit()
        print(f"  Migrated embeddings table.")

    conn.close()
    print("Guid migration complete.")


def migrate_pg_to_sqlite():
    """Migrate from pgserver to SQLite (legacy)."""
    try:
        import pgserver
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as e:
        logging.error("Could not import pgserver. For migrations, please ensure that this package is installed with [postgres] optional dependencies.")


    db = pgserver.get_server("cache_data")
    pg = psycopg.connect(db.get_uri())
    register_vector(pg)
    sq = sqlite3.connect(_DB_PATH)

    with pg.cursor() as cur:
        cur.execute("SELECT url, content, last_fetched, failed FROM link_cache")
        rows = cur.fetchall()
    print(f"Migrating {len(rows)} link_cache rows...")
    sq.executemany(
        "INSERT OR IGNORE INTO link_cache (url, content, last_fetched, failed) VALUES (?, ?, ?, ?)",
        [(url, content, last_fetched.isoformat() if last_fetched else None, int(failed))
         for url, content, last_fetched, failed in rows]
    )
    sq.commit()

    with pg.cursor() as cur:
        cur.execute("SELECT url, summary FROM summaries")
        rows = cur.fetchall()
    print(f"Migrating {len(rows)} summaries rows...")
    sq.executemany(
        "INSERT OR IGNORE INTO summaries (url, summary) VALUES (?, ?)",
        rows
    )
    sq.commit()

    with pg.cursor(binary=True) as cur:
        cur.execute("SELECT url, title, embedding FROM embeddings")
        rows = cur.fetchall()
    print(f"Migrating {len(rows)} embeddings rows...")
    sq.executemany(
        "INSERT OR IGNORE INTO embeddings (url, title, embedding) VALUES (?, ?, ?)",
        [(url, title, np.array(embedding, dtype=np.float64).tobytes()) for url, title, embedding in rows]
    )
    sq.commit()

    pg.close()
    sq.close()
    print("Migration complete.")


if __name__ == "__main__":
    import os
    if os.path.isdir("cache_data"):
        migrate_pg_to_sqlite()
        os.rmdir("cache_data")
    migrate_add_guid_if_needed()
