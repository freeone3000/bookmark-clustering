import datetime
import os
import sqlite3
from pathlib import Path

from ..bookmark_types import Bookmark

class FirefoxLoadError(Exception):
    pass

def _load_ff_content_from_cache(db_path: str, url: str, date: str) -> str | None:
    from pathlib import Path
    from .ff_cache import Cache2

    profile_dir = Path(db_path).parent
    try:
        cache = Cache2(profile_dir)
        # TODO load cache!
    except FileNotFoundError:
        return None


def _load_from_sqlite(db_path: str) -> list[Bookmark]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # folders have b.fk IS NULL; we select them out due to confidence in our clustering approach
        cursor.execute("SELECT b.guid, b.title, url, dateadded FROM moz_bookmarks AS b JOIN moz_places ON b.fk = moz_places.id WHERE b.fk IS NOT NULL ORDER BY b.guid DESC")
        bookmarks = [Bookmark(guid=row[0], title=row[1], url=row[2], date=datetime.datetime.fromtimestamp(row[3] / 1_000_000), content=_load_ff_content_from_cache(db_path=db_path, url=row[2], date=row[3])) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise FirefoxLoadError("Could not open database; is firefox running? It should not be.") from e
    finally:
        conn.close()

    return bookmarks

def _get_profile_path() -> Path:
    import platform
    if platform.system() == "Darwin":
        base_path = Path.home() / "Library/Application Support/Firefox/Profiles/"
    elif platform.system() == "Windows":
        base_path = Path(os.getenv("APPDATA")) / "Mozilla/Firefox/Profiles/"
    else:
        base_path = Path.home() / ".mozilla/firefox/"
    return base_path

def load_bookmarks() -> list[Bookmark]:
    base_path = _get_profile_path()

    # Find the default profile
    profile_path = None
    for entry in os.listdir(base_path):
        if entry.endswith(".default-release"):
            profile_path = os.path.join(base_path, entry)
            break
    if profile_path is None:
        raise FileNotFoundError("Could not find Firefox profile directory.")

    # Connect to the places.sqlite database
    db_path = os.path.join(profile_path, "places.sqlite")
    return _load_from_sqlite(db_path)