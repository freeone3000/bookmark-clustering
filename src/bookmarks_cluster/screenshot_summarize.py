import base64
import sqlite3
from typing import NamedTuple

import lmstudio as lms

from .bookmark_types import Bookmark, GUID
from .summarize import Summary
from .summarize import SYSTEM_PROMPT

VISION_MODEL = "zai-org/glm-4.6v-flash"


def _llm_extract_screenshot(screenshot: bytes) -> str:
    """
    Given a screenshot of a web page, uses a local vision LLM to summarize the page.
    :return: The page summary
    """
    import logging
    from openai import OpenAI

    b64_image = base64.b64encode(screenshot).decode("utf-8")

    while True:
        model = lms.llm(VISION_MODEL)

        try:
            client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[  # type: ignore
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Summarize the content, purpose, and intended audience of the web page shown in this screenshot. Emphasize when a user would re-visit the page.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
            )

            extracted_content = response.choices[0].message.content
            logging.info("Successfully extracted content from screenshot using LM Studio")
            return extracted_content

        except Exception as e:
            logging.error(f"Failed to extract content from screenshot using LM Studio: {e}")


def screenshot_extract_all(bookmarks: list[Bookmark], conn: sqlite3.Connection) -> list[Summary]:
    from .db import get_screenshot_summaries, write_screenshot_summary

    cached_summaries = get_screenshot_summaries(conn)
    summaries = []
    while len(bookmarks) > 0:
        bookmark = bookmarks.pop(0)
        if bookmark.screenshot is not None:
            if bookmark.guid in cached_summaries:
                summary = cached_summaries[bookmark.guid]
            else:
                summary = _llm_extract_screenshot(bookmark.screenshot)
                if len(summary) > 0:
                    write_screenshot_summary(bookmark.guid, bookmark.url, summary, conn)
            summaries.append(Summary(guid=bookmark.guid, url=bookmark.url, title=bookmark.title, summary=summary))
            del bookmark
    # unload model
    while len(lms.list_loaded_models("llm")) != 0:
        lms.llm().unload()
    return summaries
