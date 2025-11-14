from __future__ import annotations

from collections import defaultdict
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


async def fetch_profile(handle: str) -> Dict[str, Any]:
    url = f"https://codeforces.com/profile/{handle}"
    html = await _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    profile: Dict[str, Any] = {"handle": handle}

    # Current rating and rank (best-effort parsing)
    rank_el = soup.select_one(".user-rank")
    rating_el = soup.select_one(".info .user-gray, .info .user-green, .info .user-blue, .info .user-purple, .info .user-orange, .info .user-red")
    profile["rank"] = rank_el.get_text(strip=True) if rank_el else None
    profile["current_rating"] = None
    if rating_el:
        try:
            profile["current_rating"] = int(rating_el.get_text(strip=True))
        except ValueError:
            profile["current_rating"] = None

    # Max rating if visible
    max_rating = None
    for li in soup.select(".profile-info .info li"):
        text = li.get_text(" ", strip=True)
        if "Max rating" in text:
            max_rating = text
            break
    profile["max_rating_text"] = max_rating

    # Country/organization (best effort)
    for li in soup.select(".profile-info .info li"):
        text = li.get_text(" ", strip=True)
        if text.lower().startswith("organization"):
            profile["organization"] = text.split(":", 1)[-1].strip()
        if text.lower().startswith("country"):
            profile["country"] = text.split(":", 1)[-1].strip()

    return profile


async def fetch_problem_stats(handle: str) -> Dict[str, Any]:
    """
    Best-effort parsing of solved/attempted counts from the profile page.
    Full submission history scraping is intentionally avoided to reduce load.
    """
    url = f"https://codeforces.com/profile/{handle}"
    html = await _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    stats = {"solved": None, "attempted": None, "tags": [], "languages": []}

    # Parse a small table with "Solved" if present (site may change)
    solved_text = None
    for el in soup.select("._UserActivityFrame_counterValue"):
        # This selector may change; keep data optional
        solved_text = el.get_text(strip=True)
        break
    if solved_text:
        try:
            stats["solved"] = int(solved_text)
        except ValueError:
            pass

    # Tags & languages are not directly exposed; keep empty
    return stats


async def fetch_rating_history(handle: str) -> List[Dict[str, Any]]:
    """
    Rating chart data is rendered client-side; without the official API we cannot
    reliably pull the time series. Return an empty list as placeholder.
    """
    return []


async def get_codeforces_analytics(handle: str) -> Dict[str, Any]:
    profile, problem_stats, rating = await fetch_profile(handle), await fetch_problem_stats(handle), await fetch_rating_history(handle)
    return {
        "profile": profile,
        "problems": problem_stats,
        "rating_timeline": rating,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "Data extracted from public profile without API; some fields may be limited.",
    }


