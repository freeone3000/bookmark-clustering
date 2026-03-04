from datetime import datetime
import requests
from bs4 import BeautifulSoup

def fetch_site(url: str, when: datetime) -> str | None:
    """
    Fetches a site from remote using the wayback API's memento protocol support.
    This returns the *closest* snapshot to the given time, which may be in the future!
    :param url: The *original* URL site to fetch
    :param when: The point-in-time to fetch
    :return: The site content, or None if the site was never archived by archive.org
    """
    # TODO CDX support
    timestamp = when.strftime("%Y%m%d%H%M%S")
    resp = requests.get(
        "http://archive.org/wayback/available",
        params={"url": url, "timestamp": timestamp},
    )
    resp.raise_for_status()

    closest = resp.json().get("archived_snapshots", {}).get("closest")
    if not closest or not closest.get("available"):
        return None

    # The snapshot URL is a Wayback wrapper page; the actual archived content
    # is inside an <iframe id="playback"> element.
    wrapper = requests.get(closest["url"])
    wrapper.raise_for_status()

    soup = BeautifulSoup(wrapper.text, "html.parser")
    iframe = soup.find("iframe", id="playback")
    if iframe is None or not iframe.get("src"):
        return None

    inner = requests.get(iframe["src"])
    inner.raise_for_status()
    return inner.text
