from pathlib import Path
from datetime import datetime
from html import escape

from src.bookmarks_cluster.cluster import Clustering


def output_html(clustering: Clustering, file_path: Path):
    """Output bookmarks as a Firefox-compatible HTML file with clusters as folders.

    Args:
        clustering: List of Cluster objects to export
        file_path: Path where the bookmarks.html file should be saved
    """
    # Firefox bookmarks HTML format
    # Reference: https://support.mozilla.org/en-US/kb/import-bookmarks-html-file

    timestamp = int(datetime.now().timestamp() * 1000)  # Firefox uses milliseconds

    html_lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<!-- This is an automatically generated file.',
        '     It will be read and overwritten by Firefox.',
        '     DO NOT EDIT! -->',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks Menu</H1>',
        '',
        '<DL><p>',
    ]

    # Add each cluster as a folder
    for cluster in clustering:
        # Escape special HTML characters in the cluster label
        escaped_label = escape(cluster.label or "!!! NO LABEL !!!")

        # Add folder entry
        html_lines.append(f'    <DT><H3 ADD_DATE="{timestamp}" LAST_MODIFIED="{timestamp}">{escaped_label}</H3>')
        html_lines.append('    <DL><p>')

        # Add bookmarks within the folder
        for bookmark in cluster.bookmarks:
            escaped_title = escape(bookmark.title or "!!! NO TITLE !!!")
            escaped_url = escape(bookmark.url or "!!! NO URL !!!")

            html_lines.append(f'        <DT><A HREF="{escaped_url}" ADD_DATE="{timestamp}">{escaped_title}</A>')

        html_lines.append('    </DL><p>')

    html_lines.append('</DL><p>')

    # Write to file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))

