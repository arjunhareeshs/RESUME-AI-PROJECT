#!/usr/bin/env python3
"""
github_super_verifier.py
Comprehensive GitHub genuineness analyzer.

Usage:
    export GITHUB_TOKEN=ghp_...
    python github_super_verifier.py --resume-file resume.txt --username candidateUser --out super_reports
"""
import os
import re
import json
import time
import shutil
import argparse
import tempfile
import logging
from datetime import datetime
from pprint import pprint

import requests
import pandas as pd
from tqdm import tqdm

# High-level GitHub lib
from github import Github

# HTML scraping (fallback)
from bs4 import BeautifulSoup

# local git
from git import Repo, GitCommandError

# fuzzy
from rapidfuzz import fuzz

# plotting
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

# optional: pydriller for richer commit mining (try/except)
try:
    from pydriller import RepositoryMining
    PydrillerAvailable = True
except Exception:
    PydrillerAvailable = False

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("super_verifier")

# ---------------- CONFIG ----------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("Missing GITHUB_TOKEN environment variable. Set it before running.")

GH_API_REST = "https://api.github.com"
GH_API_GRAPHQL = "https://api.github.com/graphql"
g = Github(GITHUB_TOKEN)
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

# ---------------- HELPERS ----------------
def extract_github_links(text: str):
    pattern = r'https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'
    found = re.findall(pattern, text)
    def norm(u):
        u = u.rstrip('/')
        if u.endswith('.git'):
            u = u[:-4]
        return u
    return list({norm(u) for u in found})

def rest_get(path, params=None):
    """Generic GET against GH REST API path (path = 'repos/owner/repo/...')."""
    url = GH_API_REST.rstrip('/') + '/' + path.lstrip('/')
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if r.status_code == 404:
        raise ValueError(f"404 Not Found: {url}")
    r.raise_for_status()
    return r.json()

def graphql_query(query, variables=None):
    """Call GH GraphQL and return JSON (raises on non-200)."""
    r = requests.post(GH_API_GRAPHQL, headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}, json={"query": query, "variables": variables or {}}, timeout=30)
    if r.status_code != 200:
        # Propagate helpful message
        raise ValueError(f"GraphQL error {r.status_code}: {r.text}")
    data = r.json()
    if "errors" in data:
        raise ValueError(f"GraphQL returned errors: {data['errors']}")
    return data

# ---------------- METHODS ----------------
def pygithub_repo_info(full_name):
    """Use PyGithub to get repo and basic metrics."""
    repo = g.get_repo(full_name)
    info = {
        "full_name": repo.full_name,
        "name": repo.name,
        "owner": repo.owner.login,
        "private": repo.private,
        "fork": repo.fork,
        "forks_count": repo.forks_count,
        "stargazers_count": repo.stargazers_count,
        "watchers_count": repo.watchers_count,
        "size_kb": repo.size,
        "language": repo.language,
        "created_at": repo.created_at.isoformat(),
        "updated_at": repo.updated_at.isoformat(),
        "default_branch": repo.default_branch,
        "html_url": repo.html_url,
        "description": repo.description,
    }
    return info

def rest_repo_commits_count(full_name):
    """Get approximate commit count using REST pagination trick (per_page=1, check Link header)."""
    url = f"{GH_API_REST}/repos/{full_name}/commits"
    r = requests.get(url, headers=HEADERS, params={"per_page": 1}, timeout=30)
    if r.status_code == 404:
        raise ValueError(f"Repository not found: {full_name}")
    r.raise_for_status()
    link = r.headers.get('Link', '')
    if link:
        # Look for rel="last" page number
        m = re.search(r'&page=(\d+)>; rel="last"', link)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    # fallback: length of returned list
    commits = r.json()
    return len(commits)

def graphql_user_contributions_calendar(username):
    """Fetch 1-year contribution calendar (date, count) via GraphQL."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    try:
        res = graphql_query(query, {"login": username})
    except Exception as e:
        log.warning(f"GraphQL contributions fetch failed for {username}: {e}")
        return pd.DataFrame(columns=["date", "count"])
    # Navigate defensively
    weeks = res.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {}).get("weeks", [])
    days = []
    for w in weeks:
        for d in w.get("contributionDays", []):
            days.append({"date": d.get("date"), "count": d.get("contributionCount", 0)})
    df = pd.DataFrame(days)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def scrape_repo_html(full_name):
    """Scrape repo HTML page for README text and small hints (fallback)."""
    url = f"https://github.com/{full_name}"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    except Exception as e:
        return {"error": f"HTTP request failed: {e}"}
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    soup = BeautifulSoup(r.text, "html.parser")
    readme_text = ""
    readme_el = soup.find(id="readme")
    if readme_el:
        readme_text = readme_el.get_text(separator="\n").strip()
    # Heuristic: presence of fork banner or 'Forked from'
    fork_banner = False
    fork_el = soup.find(string=re.compile(r"Forked from", re.I))
    if fork_el:
        fork_banner = True
    last_commit_el = soup.find("relative-time")
    last_commit = last_commit_el['datetime'] if last_commit_el and last_commit_el.has_attr('datetime') else None
    return {"readme_text": readme_text, "fork_banner": fork_banner, "last_commit_iso": last_commit}

def clone_and_analyze(full_name, local_dir=None, shallow=True, cleanup=True):
    """
    Clone repo to temp dir and analyze:
      - commit authors and counts (via git log)
      - README content and sample file hashes
    Returns a dict with clone_dir and analysis or clone_error.
    """
    tmp = local_dir or tempfile.mkdtemp(prefix="gitclone_")
    repo_dir = os.path.join(tmp, full_name.replace("/", "_"))
    out = {"clone_dir": repo_dir}
    try:
        # embed token in URL for access (note: token will appear in git logs if printed — avoid printing)
        clone_url = f"https://{GITHUB_TOKEN}:x-oauth-basic@github.com/{full_name}.git"
        Repo.clone_from(clone_url, repo_dir, depth=1 if shallow else None)
        repo = Repo(repo_dir)
        commits = list(repo.iter_commits())
        authors = {}
        dates = []
        for c in commits:
            name = (c.author.name if c.author else None) or (c.committer.name if c.committer else "unknown")
            authors[name] = authors.get(name, 0) + 1
            dates.append(datetime.fromtimestamp(c.committed_date))
        out['commit_count_local'] = len(commits)
        out['authors_local'] = authors
        out['commit_dates_sample'] = sorted(dates)[:10]
        # README contents (common names)
        readme_text = ""
        for candidate in ("README.md", "README.rst", "README.txt", "readme.md"):
            p = os.path.join(repo_dir, candidate)
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        readme_text += fh.read() + "\n"
                except Exception:
                    pass
        out['readme_text'] = readme_text[:20000]
        # small file fingerprint sample
        file_hashes = {}
        for root, _, files in os.walk(repo_dir):
            for f in files:
                fullp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fullp)
                    if size > 5_000_000:
                        continue
                    with open(fullp, "rb") as fh:
                        chunk = fh.read(1024)
                        file_hashes[os.path.relpath(fullp, repo_dir)] = hash(chunk)
                except Exception:
                    continue
        out['file_hashes_sample'] = file_hashes
    except GitCommandError as e:
        out['clone_error'] = str(e)
    except Exception as e:
        out['clone_error'] = str(e)
    finally:
        if cleanup and os.path.exists(repo_dir):
            try:
                shutil.rmtree(repo_dir)
            except Exception:
                pass
    return out

def compare_with_upstream_if_fork(full_name):
    """If repo is a fork, try to find parent and compute README similarity."""
    try:
        repo = g.get_repo(full_name)
    except Exception as e:
        return {"error": f"Could not fetch repo metadata: {e}"}
    if not repo.fork:
        return {"is_fork": False}
    parent = None
    try:
        parent = repo.parent.full_name if repo.parent else None
    except Exception:
        parent = None
    if not parent:
        return {"is_fork": True, "parent": None}
    def get_readme_text(rname):
        try:
            content = rest_get(f"repos/{rname}/readme")
            import base64
            text = base64.b64decode(content.get('content', '')).decode('utf-8', errors='ignore')
            return text[:20000]
        except Exception:
            return ""
    mine = get_readme_text(full_name)
    theirs = get_readme_text(parent)
    sim = fuzz.token_set_ratio(mine, theirs) if mine and theirs else None
    return {"is_fork": True, "parent": parent, "readme_similarity_percent": sim}

def analyze_repo_full(full_name, claimed_username, do_clone=True):
    """Run many checks and return aggregated dict for a single repo."""
    log.info(f"Analyzing {full_name}")
    result = {}
    # 1. PyGithub metadata
    try:
        metadata = pygithub_repo_info(full_name)
        result["metadata"] = metadata
    except Exception as e:
        result["metadata_error"] = str(e)

    # 2. REST commit count
    try:
        result["rest_commit_count_estimate"] = rest_repo_commits_count(full_name)
    except Exception as e:
        result["rest_commit_count_error"] = str(e)

    # 3. GraphQL contribution calendar for claimed user (keep as summary)
    try:
        cal = graphql_user_contributions_calendar(claimed_username)
        result["claim_user_contributions_calendar"] = cal.to_dict(orient="records")
    except Exception as e:
        result["contrib_calendar_error"] = str(e)

    # 4. Scrape HTML for readme and hints
    try:
        result["scrape"] = scrape_repo_html(full_name)
    except Exception as e:
        result["scrape_error"] = str(e)

    # 5. Clone & local analysis (optional)
    if do_clone:
        try:
            clone_info = clone_and_analyze(full_name, shallow=True, cleanup=True)
            result["clone_info"] = clone_info
        except Exception as e:
            result["clone_error"] = str(e)
    else:
        result["clone_info"] = {"skipped": True}

    # 6. If fork, compare with upstream
    try:
        result["fork_compare"] = compare_with_upstream_if_fork(full_name)
    except Exception as e:
        result["fork_compare_error"] = str(e)

    # 7. PyDriller deeper authors (optional)
    if PydrillerAvailable:
        try:
            authors = {}
            for commit in RepositoryMining(f"https://github.com/{full_name}.git").traverse_commits():
                k = (commit.author.name or "unknown")
                authors[k] = authors.get(k, 0) + 1
            result['pydriller_authors_approx'] = authors
        except Exception as e:
            result['pydriller_error'] = str(e)

    # 8. Heuristics / scoring (combine many signals)
    try:
        total_commits_est = result.get("rest_commit_count_estimate") or result.get("clone_info", {}).get("commit_count_local") or 0
        author_commits_local = 0
        authors_local = result.get("clone_info", {}).get("authors_local") or {}
        for name, count in (authors_local.items()):
            if name and claimed_username.lower() in name.lower():
                author_commits_local += count
        genuine_ratio = (author_commits_local / total_commits_est) if total_commits_est else 0
        readme_sim = result.get("fork_compare", {}).get("readme_similarity_percent")
        fork = result.get("metadata", {}).get("fork", False)
        score = 0.0
        score += 0.4 * min(genuine_ratio, 1)
        score += 0.2 * (0 if fork else 1)
        score += 0.2 * min(total_commits_est / 200, 1)
        stars = result.get("metadata", {}).get("stargazers_count") or 0
        score += 0.1 * min(stars / 20, 1)
        size_kb = result.get("metadata", {}).get("size_kb") or 0
        score += 0.1 * min(size_kb / 2000, 1)
        if fork and readme_sim and readme_sim > 90:
            score *= 0.6
        result['heuristic_score'] = round(score, 3)
        result['heuristic_details'] = {"genuine_ratio": genuine_ratio, "readme_similarity": readme_sim, "fork": fork}
    except Exception as e:
        result['heuristics_error'] = str(e)

    return result

# ---------------- VISUALIZATIONS ----------------
def plot_commit_timeline_from_calendar(df_calendar, username, out_dir):
    if df_calendar.empty:
        return None
    df = df_calendar.groupby("date")["count"].sum().reset_index()
    fig = px.line(df, x="date", y="count", title=f"{username} - Daily Contributions (1yr)", markers=True)
    out_path = os.path.join(out_dir, f"{username}_commits_timeline.html")
    fig.write_html(out_path)
    return out_path

def plot_heatmap_from_calendar(df_calendar, username, out_dir):
    if df_calendar.empty:
        return None
    df_calendar['week'] = df_calendar['date'].dt.isocalendar().week
    df_calendar['weekday'] = df_calendar['date'].dt.weekday
    pivot = df_calendar.pivot_table(index='weekday', columns='week', values='count', aggfunc='sum', fill_value=0)
    plt.figure(figsize=(16, 3))
    sns.heatmap(pivot, cmap="YlGnBu", cbar=True)
    plt.title(f"{username} - Contribution Heatmap (1yr)")
    plt.ylabel("Weekday (0=Mon)")
    out_path = os.path.join(out_dir, f"{username}_heatmap.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=150)
    plt.close()
    return out_path

# ---------------- MASTER ----------------
def analyze_candidate_from_resume_text(resume_text, username, output_dir="super_reports", do_clone=True):
    os.makedirs(output_dir, exist_ok=True)
    repo_links = extract_github_links(resume_text)
    log.info(f"Found {len(repo_links)} repo link(s) in resume.")
    all_results = []
    for link in tqdm(repo_links, desc="Repos"):
        full_name = "/".join(link.split("/")[-2:])
        try:
            r = analyze_repo_full(full_name, username, do_clone=do_clone)
            r['full_name'] = full_name
            all_results.append(r)
            # small sleep to be gentle on API
            time.sleep(0.5)
        except Exception as e:
            all_results.append({"full_name": full_name, "error": str(e)})

    # Flatten to summary rows
    rows = []
    for r in all_results:
        meta = r.get("metadata") or {}
        rows.append({
            "full_name": r.get("full_name"),
            "owner": meta.get("owner"),
            "name": meta.get("name"),
            "fork": meta.get("fork"),
            "stars": meta.get("stargazers_count"),
            "forks": meta.get("forks_count"),
            "size_kb": meta.get("size_kb"),
            "rest_commit_count_est": r.get("rest_commit_count_estimate"),
            "commit_count_local": r.get("clone_info", {}).get("commit_count_local"),
            "heuristic_score": r.get("heuristic_score"),
            "readme_similarity": r.get("fork_compare", {}).get("readme_similarity_percent") if r.get("fork_compare") else None,
        })
    df = pd.DataFrame(rows)
    df['heuristic_score'] = pd.to_numeric(df['heuristic_score'], errors='coerce')
    overall = df['heuristic_score'].mean()
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "username": username,
        "repos_analyzed": len(rows),
        "overall_score": None if pd.isna(overall) else float(round(overall, 3)),
        "details": all_results,
    }

    base = os.path.join(output_dir, f"{username}_detailed_report")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    df.to_csv(base + ".csv", index=False)
    log.info(f"Saved report: {base}.json and {base}.csv")

    # calendar + plots (for username)
    try:
        calendar = graphql_user_contributions_calendar(username)
        html_path = plot_commit_timeline_from_calendar(calendar, username, output_dir)
        heatmap_path = plot_heatmap_from_calendar(calendar, username, output_dir)
        log.info(f"Saved visualizations: {html_path}, {heatmap_path}")
    except Exception as e:
        log.warning(f"Could not produce calendar plots: {e}")

    return report, df

# ---------------- CLI ----------------
def main():
    parser = argparse.ArgumentParser(description="GitHub Super Verifier - analyze repos listed in a resume text for genuineness.")
    parser.add_argument("--resume-file", required=True, help="Plain text resume containing GitHub links")
    parser.add_argument("--username", required=True, help="Claimed GitHub username for the candidate")
    parser.add_argument("--out", default="super_reports", help="Output directory")
    parser.add_argument("--no-clone", action="store_true", help="Skip cloning repositories (faster, less disk/network)")
    args = parser.parse_args()

    with open(args.resume_file, "r", encoding="utf-8", errors="ignore") as fh:
        resume_text = fh.read()

    report, df = analyze_candidate_from_resume_text(resume_text, args.username, args.out, do_clone=not args.no_clone)
    print("Overall score:", report["overall_score"])
    print("Summary table:")
    print(df.head(20).to_string(index=False))
    print("Detailed report written to:", os.path.join(args.out, f"{args.username}_detailed_report.json"))

if __name__ == "__main__":
    main()
