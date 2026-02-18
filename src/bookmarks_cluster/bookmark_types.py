from typing import NamedTuple

class Bookmark(NamedTuple):
    guid: str
    title: str
    url: str
    content: str | None = None