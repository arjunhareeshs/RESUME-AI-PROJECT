from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup  # type: ignore

HEADERS = {
    "User-Agent": "resume-ai-platform",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def _fetch_html(url: str) -> str:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def get_hackerrank_analytics(username: str) -> Dict[str, Any]:
    """
    HackerRank profile pages are heavily client-rendered; without a private API we provide a minimal scrape:
    - Basic identity and badges count (if visible in HTML)
    - Domain-wise points are often rendered client-side; set as unknown if not available
    """
    url = f"https://www.hackerrank.com/{username}"
    html = await _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    profile: Dict[str, Any] = {"username": username}

    # Attempt to read title as display name
    title = soup.title.get_text(strip=True) if soup.title else None
    profile["display"] = title

    badges = []
    for b in soup.select(".badge-list .badge-title"):
        txt = b.get_text(strip=True)
        if txt:
            badges.append(txt)

    profile["badges"] = badges

    return {
        "profile": profile,
        "domains": {
            "points": [],
            "note": "Domain points not reliably available without API; consider user export.",
        },
        "certificates": [],
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "HackerRank data is partially scraped; many elements are client-rendered.",
    }


