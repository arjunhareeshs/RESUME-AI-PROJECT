from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

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


async def get_codechef_analytics(username: str) -> Dict[str, Any]:
    url = f"https://www.codechef.com/users/{username}"
    html = await _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    profile: Dict[str, Any] = {"username": username}
    rating = None
    stars = None
    highest = None

    # Rating and stars (best-effort selectors)
    rating_el = soup.select_one(".rating-number")
    if rating_el:
        try:
            rating = int(rating_el.get_text(strip=True))
        except ValueError:
            rating = None
    star_el = soup.select_one(".rating-star")
    if star_el:
        stars = star_el.get_text(strip=True)

    # Highest rating
    for el in soup.select(".rating-header small"):
        text = el.get_text(" ", strip=True).lower()
        if "highest rating" in text:
            highest = el.get_text(" ", strip=True)
            break

    # Languages (tags list, best-effort)
    langs = []
    for tag in soup.select(".profile-about .content .tag-box a"):
        txt = tag.get_text(strip=True)
        if txt:
            langs.append(txt)

    profile.update(
        {
            "current_rating": rating,
            "stars": stars,
            "highest": highest,
            "languages": langs,
        }
    )

    return {
        "profile": profile,
        "contests": {
            "timeline": [],
            "note": "Contest history not parsed without official API; consider CSV import if needed.",
        },
        "problems": {
            "solved_total": None,
            "by_difficulty": [],
        },
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "CodeChef data scraped from public profile; some fields may be unavailable.",
    }


