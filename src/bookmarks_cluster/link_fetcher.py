import sqlite3
import logging

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
    from urllib.parse import urlsplit

    url = bookmark.url
    # skip localhost
    (_, netloc, _, _, _) = urlsplit(url)
    if netloc == 'localhost' or netloc == '::1' or netloc.startswith('127.'):
        return None

    # start fetching remote
    should_refetch = False
    content = None
    # check cache for refetch
    cursor = conn.cursor()
    cursor.execute("SELECT content, last_fetched FROM link_cache WHERE url = ? LIMIT 1", (url,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        should_refetch = True
    else:
        last_fetched_dt = datetime.datetime.fromisoformat(row[1])
        one_month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        if last_fetched_dt < one_month_ago:
            should_refetch = True
    if should_refetch:
        # noinspection PyBroadException  ...we want to catch everything to prevent a crash yeah
        try:
            logging.log(logging.INFO, f"Fetching {bookmark.url}...")
            content = _selenium_stealth_get_contents(bookmark.url)
            now = datetime.datetime.now()

            cursor = conn.cursor()
            cursor.execute("INSERT INTO link_cache (url, content, last_fetched) VALUES (?, ?, ?) ON CONFLICT(url) DO UPDATE SET content = ?, last_fetched = ?",
                       (url, content, now, content, now))
            cursor.execute("COMMIT")
            cursor.close()

            logging.log(logging.INFO, f"Fetched {bookmark.title} from {bookmark.url}")
        except:  # underlying error in fetch
            content = None
    else:
        logging.log(logging.INFO, f"Fetched {bookmark.title} from CACHE")
    return content

def fetch_bookmark_contents(bookmarks: list[Bookmark]) -> list[Bookmark]:
    fetched_bookmarks = []
    conn = sqlite3.connect("cache.sqlite")
    try:
        for bookmark in bookmarks:
            fetched_bookmark = Bookmark(bookmark.guid, bookmark.title, bookmark.url, _fetch_bookmark_content(bookmark, conn))
            fetched_bookmarks.append(fetched_bookmark)
    finally:
        conn.close()
    return bookmarks
