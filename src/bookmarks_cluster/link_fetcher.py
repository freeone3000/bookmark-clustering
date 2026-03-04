import sqlite3
import logging

from selenium import webdriver

from .db import write_cache, get_cache_entries, CacheEntry
from .bookmark_types import Bookmark
from .wayback.fetch_site import fetch_site as wayback_fetch_site

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

def _selenium_stealth_get_contents(url: str) -> tuple[str | None, bytes | None]:
    """
    Fetches a URL and returns the content and screenshot using selenium stealth
    :param url: The URL to fetch
    :return: Tuple of (page_source, screenshot_png_bytes), if successful
    :raises: Error: If not successful
    """
    driver = _get_webdriver()
    driver.get(url)
    return driver.page_source, driver.get_screenshot_as_png()

def _fetch_bookmark_content(bookmark: Bookmark, conn: sqlite3.Connection) -> CacheEntry:
    logging.log(logging.INFO, f"Fetching {bookmark.url}...")

    failed = False
    content = None
    screenshot = None
    # noinspection PyBroadException
    try:
        content, screenshot = _selenium_stealth_get_contents(bookmark.url)
    except:
        # noinspection PyBroadException
        try:
            wayback_url = wayback_fetch_site(bookmark.url, bookmark.date)
            content, screenshot = _selenium_stealth_get_contents(wayback_url)
        except:
            failed = True
    write_cache(bookmark, content, screenshot, failed, conn)
    logging.log(logging.INFO, f"Fetched {bookmark.title} from {bookmark.url}")
    return CacheEntry(content=content, screenshot=screenshot)

def fetch_bookmark_contents(bookmarks: list[Bookmark], conn: sqlite3.Connection) -> list[Bookmark]:
    fetched_bookmarks = []
    cached_urls = get_cache_entries(conn)
    for bookmark in bookmarks:
        if bookmark.url in cached_urls:
            bookmark_info: CacheEntry = cached_urls[bookmark.url]
        else:
            bookmark_info: CacheEntry = _fetch_bookmark_content(bookmark, conn)
        fetched_bookmark = Bookmark(bookmark.guid, bookmark.title, bookmark.url, bookmark.date, bookmark_info.content, bookmark_info.screenshot)
        fetched_bookmarks.append(fetched_bookmark)
    return fetched_bookmarks
