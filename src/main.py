def main():
    import os
    import logging

    from bookmarks_cluster.firefox.ff_loader import load_bookmarks
    from bookmarks_cluster.link_fetcher import fetch_bookmark_contents

    if os.path.exists("bookmarks_cluster.log"):
        os.remove("bookmarks_cluster.log")
    logging.basicConfig(level=logging.INFO)

    bookmarks = fetch_bookmark_contents(load_bookmarks())
    print("Fetched")

if __name__ == "__main__":
    main()