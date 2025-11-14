from collections import defaultdict, Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ...config import settings

BASE = "https://huggingface.co/api"


def _auth_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "resume-ai-platform",
    }
    if settings.HF_TOKEN:
        headers["Authorization"] = f"Bearer {settings.HF_TOKEN}"
    return headers


async def _get_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None):
    resp = await client.get(url, headers=_auth_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def fetch_user(username: str) -> Dict[str, Any]:
    url = f"{BASE}/users/{username}"
    async with httpx.AsyncClient() as client:
        data = await _get_json(client, url)
        return {
            "name": data.get("name"),
            "fullname": data.get("fullname"),
            "avatarUrl": data.get("avatarUrl"),
            "type": data.get("type"),  # user / org
            "bio": data.get("bio"),
            "website": data.get("website"),
            "location": data.get("location"),
            "joined": data.get("joined"),
            "likes": data.get("likes"),
        }


async def fetch_models(username: str) -> List[Dict[str, Any]]:
    # https://huggingface.co/api/models?author={username}&full=true
    url = f"{BASE}/models"
    params = {"author": username, "full": "true"}
    async with httpx.AsyncClient() as client:
        return await _get_json(client, url, params=params)


async def fetch_datasets(username: str) -> List[Dict[str, Any]]:
    # https://huggingface.co/api/datasets?author={username}&full=true
    url = f"{BASE}/datasets"
    params = {"author": username, "full": "true"}
    async with httpx.AsyncClient() as client:
        return await _get_json(client, url, params=params)


async def fetch_spaces(username: str) -> List[Dict[str, Any]]:
    # https://huggingface.co/api/spaces?author={username}&full=true
    url = f"{BASE}/spaces"
    params = {"author": username, "full": "true"}
    async with httpx.AsyncClient() as client:
        return await __get_json(client, url, params=params)


def _agg_items(items: List[Dict[str, Any]], kind: str) -> Dict[str, Any]:
    total = len(items)
    likes = sum(i.get("likes", 0) or 0 for i in items)
    downloads = sum(i.get("downloads", 0) or 0 for i in items)
    # pipeline_tag for models/spaces; task categories
    tag_counter: Counter = Counter()
    langs_counter: Counter = Counter()
    monthly: Dict[str, int] = defaultdict(int)

    for i in items:
        # date fields: lastModified or lastModified (ISO string)
        last = i.get("lastModified") or i.get("updatedAt") or i.get("siblings")  # siblings is not date; keep safe
        date_str = i.get("lastModified") or i.get("cardData", {}).get("last_modified")
        # fallback to 'lastModified' present on most entries
        ds = i.get("lastModified")
        if isinstance(ds, str) and len(ds) >= 7:
            month = ds[:7]
            monthly[month] += 1

        tag = i.get("pipeline_tag")
        if tag:
            tag_counter.update([tag])

        # languages sometimes in cardData or tags
        card_langs = i.get("cardData", {}).get("language")
        if isinstance(card_langs, list):
            langs_counter.update([l for l in card_langs if isinstance(l, str)])
        tags = i.get("tags") or []
        for t in tags:
            if isinstance(t, str) and t.startswith("languages:"):
                langs_counter.update([t.split(":", 1)[1]])

    top_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(15)]
    top_langs = [{"language": l, "count": c} for l, c in langs_counter.most_common(15)]
    monthly_activity = [{"month": m, "count": monthly[m]} for m in sorted(monthly.keys())]

    return {
        "kind": kind,
        "total": total,
        "likes": likes,
        "downloads": downloads,
        "top_pipeline_tags": top_tags,
        "top_languages": top_langs,
        "monthly_activity": monthly_activity,
        "recent": [
            {
                "id": i.get("id"),
                "sha": i.get("sha"),
                "private": i.get("private"),
                "likes": i.get("likes", 0),
                "downloads": i.get("downloads", 0),
                "lastModified": i.get("lastModified"),
                "pipeline_tag": i.get("pipeline_tag"),
            }
            for i in items[:12]
        ],
    }


async def get_hf_analytics(username: str) -> Dict[str, Any]:
    models, datasets, spaces, user = await httpx.AsyncClient().run(None)  # type: ignore
    # The above line is a placeholder; we’ll fetch concurrently below.
    async with httpx.AsyncClient() as client:
        # Fetch in sequence to keep it simple and robust; can switch to asyncio.gather if desired.
        user = await _get_json(client, f"{BASE}/users/{username}")
        models = await _get_json(client, f"{BASE}/models", params={"author": username, "full": "true"})
        datasets = await _get_json(client, f"{BASE}/datasets", params={"author": username, "full": "true"})
        spaces = await _get_json(client, f"{BASE}/spaces", params={"author": username, "full": "true"})

    models_summary = _agg_items(models, "models")
    datasets_summary = _agg_items(datasets, "datasets")
    spaces_summary = _agg_items(spaces, "spaces")

    profile = {
        "username": username,
        "name": user.get("name"),
        "fullname": user.get("fullname"),
        "avatarUrl": user.get("avatarUrl"),
        "type": user.get("type"),
        "bio": user.get("bio"),
        "website": user.get("website"),
        "location": user.get("location"),
        "joined": user.get("joined"),
        "likes": user.get("likes"),
    }

    return {
        "profile": profile,
        "models": models_summary,
        "datasets": datasets_summary,
        "spaces": spaces_summary,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }

