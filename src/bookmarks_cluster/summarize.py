from typing import NamedTuple

import psycopg

from .bookmark_types import Bookmark

class Summary(NamedTuple):
    url: str
    title: str
    summary: str

def _llm_extract(html: str) -> str:
    """
    Given an HTML page, uses a local LLM to extract the "meaningful" page contents.
    Truncates HTML to 44,351 tokens to prevent context overflow.
    :return: The page contents
    """
    import logging
    from openai import OpenAI

    try:
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

        # Truncate HTML to prevent token overflow (estimate ~4 chars per token); max length found was 4435132
        max_chars = 130_000 * 4
        truncated_html = html[:max_chars]
        if len(html) > max_chars:
            truncated_html += "\n[... content truncated ...]"

        response = client.chat.completions.create(
            model="local-model",
            messages=[  # type: ignore
                {
                    "role": "system",
                    "content": "You are an expert at extracting meaningful content from HTML pages. Extract the main content, article body, and key information while removing HTML markup, navigation elements, ads, scripts, and boilerplate. Return only the cleaned, meaningful text content."
                },
                {
                    "role": "user",
                    "content": f"Extract the meaningful content from this HTML:\n\n{truncated_html}"
                }
            ],
            temperature=0.3,
        )

        extracted_content = response.choices[0].message.content

        # find the first double newline after the </think> tag, if it exists, and remove everything before that to eliminate "thinking" text
        start_idx = extracted_content.index("</think>")+len("</think>") if "</think>" in extracted_content else 0
        extracted_content = extracted_content[extracted_content.find("\n\n", start_idx)+2:]

        logging.info(f"Successfully extracted content using LM Studio")
        return extracted_content

    except Exception as e:
        logging.warning(f"Failed to extract content using LM Studio: {e}")
        return ""

def llm_extract_all(bookmarks: list[Bookmark], conn: psycopg.Connection) -> list[Summary]:
    from .db import get_summaries, write_summary

    cached_summaries = get_summaries(conn)
    summaries = []
    for bookmark in bookmarks:
        if bookmark.content is not None: # skip missing and failed
            if bookmark.url in cached_summaries:
                summary = cached_summaries[bookmark.url]
            else:
                summary = _llm_extract(bookmark.content)
                write_summary(bookmark.url, summary, conn)
            summaries.append(Summary(url=bookmark.url, title=bookmark.title, summary=summary))
    return summaries