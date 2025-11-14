import httpx

API_URL = "https://api.github.com/users"

async def fetch_github_stats(github_link: str) -> dict:
    """
    Fetches public repo data from GitHub.
    """
    username = github_link.split("/")[-1]
    if not username:
        return {"error": "Invalid GitHub link"}
        
    async with httpx.AsyncClient() as client:
        try:
            # 1. Get user summary
            # user_resp = await client.get(f"{API_URL}/{username}")
            # user_resp.raise_for_status()
            # user_data = user_resp.json()
            
            # 2. Get repos
            # repos_resp = await client.get(f"{API_URL}/{username}/repos?per_page=100")
            # repos_resp.raise_for_status()
            # repos_data = repos_resp.json()
            
            # languages = [r['language'] for r in repos_data if r['language']]
            
            # MOCK DATA
            return {
                "public_repos": 5, # user_data['public_repos'],
                "top_languages": ["Python", "TypeScript"], # list(set(languages)),
                "total_stars": 10 # sum(r['stargazers_count'] for r in repos_data)
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code}"}