from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ... import models, schemas
from ..deps import get_db, get_current_admin_user
from ...services.external import (
    github_api,
    github_analytics,
    huggingface_analytics,
    codeforces_analytics,
    codechef_analytics,
    hackerrank_analytics,
    leetcode_analytics,
)

router = APIRouter()

@router.get("/fetch_profiles", response_model=schemas.user.User)
async def fetch_profiles_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Trigger a fetch of GitHub/LeetCode stats for a specific user.
    """
    user = db.query(models.user.User).filter(models.user.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.github_link:
        user.github_stats = await github_api.fetch_github_stats(user.github_link)
        
    if user.leetcode_link:
        # Store full analytics snapshot; frontend can pick what to visualize
        username = user.leetcode_link.rstrip("/").split("/")[-1]
        user.leetcode_stats = await leetcode_analytics.get_leetcode_analytics(username)

    db.commit()
    db.refresh(user)
    
    return user


@router.get("/github/{username}/analytics")
async def get_github_analytics(
    username: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve detailed analytics for a GitHub user.
    """
    analytics = await github_analytics.get_github_analytics(username)
    return analytics


@router.get("/huggingface/{username}/analytics")
async def get_huggingface_analytics(
    username: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve detailed analytics for a Hugging Face user.
    """
    analytics = await huggingface_analytics.get_hf_analytics(username)
    return analytics


@router.get("/codeforces/{handle}/analytics")
async def get_codeforces_analytics(
    handle: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve analytics for a Codeforces user (scraped, no API).
    """
    return await codeforces_analytics.get_codeforces_analytics(handle)


@router.get("/codechef/{username}/analytics")
async def get_codechef_analytics(
    username: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve analytics for a CodeChef user (scraped, no API).
    """
    return await codechef_analytics.get_codechef_analytics(username)


@router.get("/hackerrank/{username}/analytics")
async def get_hackerrank_analytics(
    username: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve analytics for a HackerRank user (scraped, no API).
    """
    return await hackerrank_analytics.get_hackerrank_analytics(username)


@router.get("/leetcode/{username}/analytics")
async def get_leetcode_analytics(
    username: str,
    admin_user: models.user.User = Depends(get_current_admin_user),
):
    """
    Admin-only: Retrieve analytics for a LeetCode user (scraped, no API).
    """
    return await leetcode_analytics.get_leetcode_analytics(username)