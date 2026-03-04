from src.bookmarks_cluster.cluster import print_clusters_tree
from src.bookmarks_cluster.firefox.ff_output_html import output_html

from pathlib import Path

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

    conn = db_connect()
    try: # sqlite has limited 'with' support
        bookmarks = fetch_bookmark_contents(load_bookmarks(), conn)
        summaries = llm_extract_all(bookmarks, conn)
        del bookmarks
        embeddings = embed_all(summaries, conn)
        clusters = cluster(embeddings)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    output_html(clusters, Path(__file__).parent.parent / "output/bookmarks_clustered.html")

if __name__ == "__main__":
    main()