"""One-time migration from pgserver to SQLite."""
import pgserver
import psycopg
import numpy as np
from pgvector.psycopg import register_vector

# noinspection PyProtectedMember
from src.bookmarks_cluster.db import _init_db


def _pg_connect() -> psycopg.Connection:
    db = pgserver.get_server("cache_data")
    conn = psycopg.connect(db.get_uri())
    register_vector(conn)
    return conn


def migrate_pg_to_sqlite():
    pg = _pg_connect()
    sq = _init_db()

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
