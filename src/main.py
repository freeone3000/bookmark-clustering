def main():
    import os
    import logging
    from datetime import datetime

    from bookmarks_cluster.firefox.ff_loader import load_bookmarks
    from bookmarks_cluster.link_fetcher import fetch_bookmark_contents
    from bookmarks_cluster.db import db_connect
    from bookmarks_cluster.summarize import _llm_extract

    if os.path.exists("bookmarks_cluster.log"):
        os.remove("bookmarks_cluster.log")
    logging.basicConfig(level=logging.INFO)

    with db_connect() as conn:
        bookmarks = fetch_bookmark_contents(load_bookmarks(), conn)
    print(_llm_extract(bookmarks[0].content))

if __name__ == "__main__":
    main()