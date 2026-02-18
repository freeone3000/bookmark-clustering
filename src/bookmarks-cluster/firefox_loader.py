from typing import List, NamedTuple

class FirefoxLoadError(Exception):
    pass


class Bookmark(NamedTuple):
    guid: str
    title: str
    url: str

def _load_from_sqlite(db_path: str) -> List[Bookmark]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # folders have b.fk IS NULL; we select them out due to confidence in our clustering approach
        cursor.execute("SELECT b.guid, b.title, url FROM moz_bookmarks AS b JOIN moz_places ON b.fk = moz_places.id WHERE b.fk IS NOT NULL")
        bookmarks = [Bookmark(row[0], row[1], row[2]) for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        raise FirefoxLoadError("Could not open database; is firefox running?") from e
    finally:
        conn.close()

    return bookmarks

def load_bookmarks() -> List[Bookmark]:
    import platform

    if platform.system() == "Darwin":
        base_path = "/Users/jasmine/Library/Application Support/Firefox/Profiles/"
    else:
        raise NotImplementedError("Unsupported platform: {}".format(platform.system()))

    # Find the default profile
    import os
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