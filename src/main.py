
def main():
    from bookmarks_cluster.firefox.ff_loader import load_bookmarks
    from bookmarks_cluster.link_fetcher import fetch_bookmark_contents
    bookmarks = fetch_bookmark_contents(load_bookmarks())
    print("Fetched")

if __name__ == "__main__":
    main()