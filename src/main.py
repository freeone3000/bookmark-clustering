def main():
    import os
    import logging

    from bookmarks_cluster.firefox.ff_loader import load_bookmarks
    from bookmarks_cluster.link_fetcher import fetch_bookmark_contents
    from bookmarks_cluster.db import db_connect
    from bookmarks_cluster.summarize import llm_extract_all
    from bookmarks_cluster.embed import embed_all
    from src.bookmarks_cluster.cluster import cluster

    if os.path.exists("bookmarks_cluster.log"):
        os.remove("bookmarks_cluster.log")
    logging.basicConfig(level=logging.INFO)

    with db_connect() as conn:
        bookmarks = fetch_bookmark_contents(load_bookmarks(), conn)
        summaries = llm_extract_all(bookmarks, conn)
        del bookmarks
        embeddings = embed_all(summaries, conn)
        print(cluster(embeddings))

if __name__ == "__main__":
    main()