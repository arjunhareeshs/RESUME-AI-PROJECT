import asyncio
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup  # type: ignore

from ...config import settings

API_BASE = "https://api.github.com"
USER_ENDPOINT = f"{API_BASE}/users/{{username}}"
REPOS_ENDPOINT = f"{API_BASE}/users/{{username}}/repos"


def _auth_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "resume-ai-platform",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def _get_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    response = await client.get(url, headers=_auth_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


async def fetch_profile(username: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        data = await _get_json(client, USER_ENDPOINT.format(username=username))
        return {
            "username": data.get("login"),
            "name": data.get("name"),
            "avatar_url": data.get("avatar_url"),
            "bio": data.get("bio"),
            "company": data.get("company"),
            "blog": data.get("blog"),
            "location": data.get("location"),
            "email": data.get("email"),
            "hireable": data.get("hireable"),
            "public_repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
            "following": data.get("following", 0),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }


async def fetch_repositories(username: str) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            data = await _get_json(
                client,
                REPOS_ENDPOINT.format(username=username),
                params={
                    "per_page": 100,
                    "page": page,
                    "type": "owner",
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            if not data:
                break

            repos.extend(data)
            if len(data) < 100:
                break
            page += 1

    return repos


async def fetch_languages_for_repos(repos: List[Dict[str, Any]]) -> Counter:
    language_totals: Counter = Counter()

    async with httpx.AsyncClient() as client:
        for repo in repos:
            lang_url = repo.get("languages_url")
            if not lang_url:
                continue

            try:
                lang_data = await _get_json(client, lang_url)
            except httpx.HTTPStatusError:
                continue

            language_totals.update(lang_data)

    return language_totals


def build_language_summary(language_totals: Counter) -> Dict[str, Any]:
    total_bytes = sum(language_totals.values())
    languages = []

    for language, byte_count in language_totals.most_common():
        percentage = round((byte_count / total_bytes) * 100, 2) if total_bytes else 0
        languages.append(
            {
                "language": language,
                "bytes": byte_count,
                "percentage": percentage,
            }
        )

    return {
        "total_languages": len(language_totals),
        "languages": languages,
        "primary_language": languages[0]["language"] if languages else None,
    }


def build_repo_summary(repos: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(repos)
    forks = sum(1 for repo in repos if repo.get("fork"))
    originals = total - forks
    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    watchers = sum(repo.get("watchers_count", 0) for repo in repos)

    topics_counter: Counter = Counter()
    for repo in repos:
        topics = repo.get("topics") or []
        topics_counter.update(topics)

    top_topics = [{"topic": topic, "count": count} for topic, count in topics_counter.most_common(20)]

    recent_repos = [
        {
            "name": repo.get("name"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "is_fork": repo.get("fork"),
            "updated_at": repo.get("updated_at"),
            "created_at": repo.get("created_at"),
            "html_url": repo.get("html_url"),
        }
        for repo in repos[:10]
    ]

    return {
        "total_repos": total,
        "original_repos": originals,
        "forked_repos": forks,
        "total_stars": stars,
        "total_watchers": watchers,
        "top_topics": top_topics,
        "recent_repos": recent_repos,
    }


async def fetch_contribution_heatmap(username: str) -> Dict[str, Any]:
    url = f"https://github.com/users/{username}/contributions"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_auth_headers(), timeout=30)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    heatmap_data: List[Dict[str, Any]] = []
    totals_by_month: Dict[str, int] = defaultdict(int)

    for rect in soup.select("rect[data-date]"):
        date_str = rect["data-date"]
        count = int(rect.get("data-count", 0))
        level = int(rect.get("data-level", 0))

        heatmap_data.append(
            {
                "date": date_str,
                "count": count,
                "level": level,
            }
        )

        month = date_str[:7]  # YYYY-MM
        totals_by_month[month] += count

    total_contributions = sum(entry["count"] for entry in heatmap_data)

    monthly_activity = [
        {"month": month, "contributions": totals_by_month[month]}
        for month in sorted(totals_by_month.keys())
    ]

    return {
        "total_contributions": total_contributions,
        "heatmap": heatmap_data,
        "monthly_activity": monthly_activity,
    }


def build_activity_timeline(repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    timeline: Dict[str, Dict[str, int]] = defaultdict(lambda: {"created": 0, "updated": 0})

    for repo in repos:
        created = repo.get("created_at")
        updated = repo.get("updated_at")

        if created:
            created_month = created[:7]
            timeline[created_month]["created"] += 1

        if updated:
            updated_month = updated[:7]
            timeline[updated_month]["updated"] += 1

    return [
        {
            "month": month,
            "created": timeline[month]["created"],
            "updated": timeline[month]["updated"],
        }
        for month in sorted(timeline.keys())
    ]


async def get_github_analytics(username: str) -> Dict[str, Any]:
    repos, profile, contributions = await asyncio.gather(
        fetch_repositories(username),
        fetch_profile(username),
        fetch_contribution_heatmap(username),
    )

    language_totals = await fetch_languages_for_repos(repos)

    language_summary = build_language_summary(language_totals)
    repo_summary = build_repo_summary(repos)
    activity_timeline = build_activity_timeline(repos)

    return {
        "profile": profile,
        "repositories": repo_summary,
        "languages": language_summary,
        "contributions": contributions,
        "activity_timeline": activity_timeline,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }



