import sqlite3
import logging

import selenium
from selenium import webdriver

from .bookmark_types import Bookmark

_webdriver = None

def _get_webdriver() -> webdriver.Chrome:
    from selenium_stealth import stealth
    global _webdriver

    if _webdriver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        _webdriver = webdriver.Chrome(options=options)

        stealth(_webdriver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
    return _webdriver

def _selenium_stealth_get_contents(url: str) -> str | None:
    """
    Fetches a URL and returns the content using selenium stealth
    :param url: The URL to fetch
    :return: The body, if successful
    :raises: Error: If not successful
    """
    driver = _get_webdriver()
    driver.get(url)
    return driver.page_source

def _fetch_bookmark_content(bookmark: Bookmark, conn: sqlite3.Connection) -> str | None:
    import datetime
    logging.log(logging.INFO, f"Fetching {bookmark.url}...")

    failed = False
    content = None
    try:
        content = _selenium_stealth_get_contents(bookmark.url)
    except:
        failed = True
    now = datetime.datetime.now().isoformat()

    cursor = conn.cursor()
    cursor.execute("INSERT INTO link_cache (url, content, last_fetched, failed) VALUES (?, ?, ?, ?) ON CONFLICT(url) DO UPDATE SET content = ?, last_fetched = ?, failed = ?",
               (bookmark.url, content, now, failed, content, now, failed))
    cursor.execute("COMMIT")
    cursor.close()

    logging.log(logging.INFO, f"Fetched {bookmark.title} from {bookmark.url}")

def fetch_bookmark_contents(bookmarks: list[Bookmark]) -> list[Bookmark]:
    import datetime

    fetched_bookmarks = []
    conn = sqlite3.connect("cache.sqlite")
    cursor = conn.cursor()
    cmp_date: str = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()

    cursor.execute("SELECT (url) FROM link_cache WHERE last_fetched > ?", (cmp_date,))
    exclude_urls = [row[0] for row in cursor.fetchall()]
    try:
        for bookmark in bookmarks:
            if bookmark.url not in exclude_urls:
                fetched_bookmark = Bookmark(bookmark.guid, bookmark.title, bookmark.url, _fetch_bookmark_content(bookmark, conn))
                fetched_bookmarks.append(fetched_bookmark)
    finally:
        conn.close()
    return bookmarks
