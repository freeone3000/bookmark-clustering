from typing import NamedTuple

import psycopg
import lmstudio as lms

from .bookmark_types import Bookmark

SUMMARIZATION_MODEL = "phi-3.1-mini-128k-instruct"

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

    while True: # inline retry to limit stack depth
        model = lms.llm(SUMMARIZATION_MODEL) # ensure model has been reloaded; this one's a bit crashy

        # TODO a thinking model is overkill here; we might speed up summarization ability *and accuracy* using a smaller model...
        # TODO or should we go full kimi and do it based on pixels and a screenshot rather than the raw text?
        try:
            client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

            # Truncate HTML to prevent token overflow; max length found was 4435132, but max token length we have with Phi-3 is 131072
            max_chars = 130_000 # must also include truncation, system context, and the prompt below.
            truncated_html = html[:max_chars]
            if len(html) > max_chars:
                truncated_html += "\n[... content truncated ...]"

            response = client.chat.completions.create(
                model=SUMMARIZATION_MODEL,
                messages=[  # type: ignore
                    {
                        "role": "system",
                        "content": "You are an expert librarian, doing an initial summarization pass of a list of web pages. Given an HTML page, you are able to extract the content, purpose, and intended audience of the page. You will return only plain text, free from any tags or other markup."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize the content, purpose, and intended audience of the following HTML:\n\n{truncated_html}"
                    }
                ],
                temperature=0.3,
            )

            # phi has much cleaner output; likely what we should have used from the beginning
            extracted_content = response.choices[0].message.content
            logging.info(f"Successfully extracted content using LM Studio")
            return extracted_content

        except Exception as e:
            logging.error(f"Failed to extract content using LM Studio: {e}")

def llm_extract_all(bookmarks: list[Bookmark], conn: psycopg.Connection) -> list[Summary]:
    from .db import get_summaries, write_summary

    cached_summaries = get_summaries(conn)
    summaries = []
    while len(bookmarks) > 0:
        bookmark = bookmarks.pop(0) # remove as we go to limit ram usage
        if bookmark.content is not None: # skip missing and failed
            if bookmark.url in cached_summaries:
                summary = cached_summaries[bookmark.url]
            else:
                summary = _llm_extract(bookmark.content)
                if len(summary) > 0:
                    write_summary(bookmark.url, summary, conn)
            summaries.append(Summary(url=bookmark.url, title=bookmark.title, summary=summary))
            del bookmark # free memory
    # unload summarization model
    while len(lms.list_loaded_models("llm")) != 0:
        lms.llm().unload()
    return summaries