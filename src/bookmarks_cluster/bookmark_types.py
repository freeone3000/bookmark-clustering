from typing import NamedTuple
import datetime

GUID = str

class Bookmark(NamedTuple):
    guid: GUID
    title: str
    url: str
    date: datetime.datetime
    content: str | None = None