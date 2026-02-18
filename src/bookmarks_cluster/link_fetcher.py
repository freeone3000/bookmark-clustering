import sqlite3
import logging

import psycopg
from selenium import webdriver

from .db import write_cache, get_cache_entries
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

def _fetch_bookmark_content(bookmark: Bookmark, conn: psycopg.Connection) -> str | None:
    import db
    logging.log(logging.INFO, f"Fetching {bookmark.url}...")

    failed = False
    content = None
    # noinspection PyBroadException
    try:
        content = _selenium_stealth_get_contents(bookmark.url)
    except:
        failed = True
    write_cache(bookmark, content, failed, conn)

    logging.log(logging.INFO, f"Fetched {bookmark.title} from {bookmark.url}")

def fetch_bookmark_contents(bookmarks: list[Bookmark], conn: psycopg.Connection) -> list[Bookmark]:
    fetched_bookmarks = []
    cached_urls = get_cache_entries(conn)
    for bookmark in bookmarks:
        if bookmark.url in cached_urls:
            fetched_bookmark = Bookmark(bookmark.guid, bookmark.title, bookmark.url, cached_urls[bookmark.url])
        else:
            fetched_bookmark = Bookmark(bookmark.guid, bookmark.title, bookmark.url, _fetch_bookmark_content(bookmark, conn))
        fetched_bookmarks.append(fetched_bookmark)
    return fetched_bookmarks
