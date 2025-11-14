from __future__ import annotations

import json
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


def _safe_get(d: Any, path: List[str], default=None):
    cur = d
    try:
        for k in path:
            if isinstance(cur, dict):
                cur = cur.get(k)
            else:
                return default
        return cur if cur is not None else default
    except Exception:
        return default


def _parse_next_data(html: str) -> Dict[str, Any]:
    """
    LeetCode profile pages are Next.js apps. Public data is embedded in a script tag with id="__NEXT_DATA__".
    We'll parse it and extract stable fields if present. LeetCode may change structure at any time; code is defensive.
    """
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script or not script.string:
        return {}
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return {}


def _build_heatmap(submission_calendar: str | Dict[str, Any]) -> Dict[str, Any]:
    """
    submissionCalendar in LC is often a JSON string mapping unix_timestamp->count.
    """
    data_map: Dict[str, int] = {}
    if isinstance(submission_calendar, str):
        try:
            data_map = json.loads(submission_calendar)
        except json.JSONDecodeError:
            data_map = {}
    elif isinstance(submission_calendar, dict):
        data_map = {str(k): int(v) for (k, v) in submission_calendar.items()}

    heatmap = []
    monthly = defaultdict(int)
    total = 0

    for ts_str, count in data_map.items():
        try:
            ts = int(ts_str)
            date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            # Sometimes key may already be a date
            date = ts_str
        c = int(count)
        total += c
        heatmap.append({"date": date, "count": c})
        monthly[date[:7]] += c

    monthly_activity = [{"month": m, "submissions": monthly[m]} for m in sorted(monthly.keys())]
    return {"total_submissions": total, "heatmap": heatmap, "monthly_activity": monthly_activity}


def _difficulty_breakdown(next_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Try multiple known paths used historically by LeetCode
    # 1) pagesProps.profileCommunity/progressBar, or matchedUser.submitStatsGlobal
    diffs: Dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}

    ac_list = _safe_get(
        next_data,
        ["props", "pageProps", "dehydratedState", "queries", 0, "state", "data", "matchedUser", "submitStats", "acSubmissionNum"],
    )
    if isinstance(ac_list, list):
        for item in ac_list:
            difficulty = item.get("difficulty")
            count = int(item.get("count", 0) or 0)
            if difficulty in diffs:
                diffs[difficulty] += count

    # Fallback older path
    if sum(diffs.values()) == 0:
        progress = _safe_get(next_data, ["props", "pageProps", "profileCommunity", "submissionProgress"], {})
        if isinstance(progress, dict):
            diffs["Easy"] = int(progress.get("easySolved", 0))
            diffs["Medium"] = int(progress.get("mediumSolved", 0))
            diffs["Hard"] = int(progress.get("hardSolved", 0))

    return [{"difficulty": k, "solved": v} for k, v in diffs.items()]


def _languages_stats(next_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Try to infer languages used by looking at 'languageProblemCount' if present in public data.
    """
    langs = _safe_get(
        next_data,
        ["props", "pageProps", "dehydratedState", "queries", 0, "state", "data", "matchedUser", "languageProblemCount"],
        [],
    )
    results = []
    if isinstance(langs, list):
        for item in langs:
            lang = item.get("languageName")
            solved = int(item.get("problemsSolved", 0) or 0)
            if lang:
                results.append({"language": lang, "solved": solved})
    return results


async def get_leetcode_analytics(username: str) -> Dict[str, Any]:
    """
    Scrape the LeetCode public profile page (no API). Extract:
    - submission heatmap
    - difficulty breakdown
    - language problem counts (if available)
    - basic profile fields (if present)
    """
    url = f"https://leetcode.com/{username}/"
    html = await _fetch_html(url)
    next_data = _parse_next_data(html)

    # Profile basics (best effort)
    profile = {
        "username": username,
        "name": _safe_get(next_data, ["props", "pageProps", "profileCommunity", "profile", "realName"]),
        "avatar": _safe_get(next_data, ["props", "pageProps", "profileCommunity", "profile", "userAvatar"]),
        "ranking": _safe_get(next_data, ["props", "pageProps", "dehydratedState", "queries", 0, "state", "data", "matchedUser", "ranking"]),
    }

    # Submission calendar
    submission_calendar = _safe_get(
        next_data,
        ["props", "pageProps", "dehydratedState", "queries", 0, "state", "data", "matchedUser", "submissionCalendar"],
        {},
    )
    heatmap = _build_heatmap(submission_calendar)

    difficulties = _difficulty_breakdown(next_data)
    languages = _languages_stats(next_data)

    return {
        "profile": profile,
        "submissions": heatmap,
        "difficulties": difficulties,
        "languages": languages,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "This data is parsed from public Next.js payload; fields may change.",
    }


