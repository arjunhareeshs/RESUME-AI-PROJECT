import os
import re
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
from github import Github
from tqdm import tqdm
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from datetime import datetime

# ---------------- CONFIG ----------------
load_dotenv()
TOKEN = os.getenv("GITHUB_TOKEN")
if not TOKEN:
    st.error("⚠️ Missing GITHUB_TOKEN. Please set it in your .env file.")
    st.stop()

g = Github(TOKEN)

# ---------------- HELPERS ----------------
def extract_github_links(text: str):
    pattern = r'https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'
    return list(set(re.findall(pattern, text)))


def fetch_commit_activity(username: str):
    """Fetch 1-year contribution stats from GitHub GraphQL API"""
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
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.post("https://api.github.com/graphql",
                      json={"query": query, "variables": {"login": username}},
                      headers=headers)
    data = r.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    all_days = []
    for w in weeks:
        for d in w["contributionDays"]:
            all_days.append(d)
    df = pd.DataFrame(all_days)
    df["date"] = pd.to_datetime(df["date"])
    return df


def analyze_repo(repo_url: str, username: str):
    try:
        user_repo = "/".join(repo_url.split("/")[-2:])
        repo = g.get_repo(user_repo)
        commits = list(repo.get_commits())
        total_commits = len(commits)
        author_commits = sum(
            1 for c in commits if c.commit.author and c.commit.author.name and username.lower() in c.commit.author.name.lower()
        )
        genuine_ratio = author_commits / total_commits if total_commits else 0
        score = (
            (0.4 * genuine_ratio)
            + (0.2 * (0 if repo.fork else 1))
            + (0.2 * min(total_commits / 100, 1))
            + (0.1 * min(repo.stargazers_count / 10, 1))
            + (0.1 * min(repo.size / 1000, 1))
        )
        return {
            "repo": repo.name,
            "url": repo_url,
            "fork": repo.fork,
            "stars": repo.stargazers_count,
            "commits": total_commits,
            "author_commits": author_commits,
            "genuine_ratio": round(genuine_ratio, 2),
            "score": round(score, 2),
            "updated": repo.updated_at.date(),
        }
    except Exception as e:
        return {"repo": repo_url.split('/')[-1], "error": str(e)}


def analyze_candidate(resume_text, username):
    links = extract_github_links(resume_text)
    results = [analyze_repo(l, username) for l in tqdm(links)]
    df = pd.DataFrame(results)
    df["overall_genuineness"] = df["score"].mean().round(2)
    return df


def plot_commit_timeline(df_commits):
    df_daily = df_commits.groupby("date")["contributionCount"].sum().reset_index()
    fig = px.line(df_daily, x="date", y="contributionCount",
                  title="📈 Commit Consistency Over Time",
                  markers=True)
    fig.update_traces(line=dict(width=2))
    st.plotly_chart(fig, use_container_width=True)


def plot_commit_heatmap(df_commits):
    df_commits["week"] = df_commits["date"].dt.isocalendar().week
    df_commits["weekday"] = df_commits["date"].dt.weekday
    pivot = df_commits.pivot_table(index="weekday", columns="week", values="contributionCount", aggfunc="sum", fill_value=0)

    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(pivot, cmap="YlGnBu", ax=ax, cbar=True)
    ax.set_title("🔥 GitHub Commit Heatmap (1 Year)")
    ax.set_ylabel("Day of Week")
    ax.set_xlabel("Week of Year")
    st.pyplot(fig)


# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="GitHub Genuineness Verifier", layout="wide")

st.title("🧠 GitHub Genuineness & Consistency Analyzer")
st.markdown("Upload resume text or paste GitHub links to analyze authenticity of contributions.")

resume_text = st.text_area("📝 Paste Resume Text (with GitHub links)", height=200)
username = st.text_input("👤 GitHub Username (case-sensitive)", "")

if st.button("🔍 Analyze"):
    if not username:
        st.error("Please enter GitHub username.")
        st.stop()

    with st.spinner("Analyzing... this may take a minute ⏳"):
        df_repos = analyze_candidate(resume_text, username)
        df_commits = fetch_commit_activity(username)

    # ---- Repo genuineness table ----
    st.subheader("📊 Repository Genuineness Report")
    st.dataframe(df_repos, use_container_width=True)

    st.metric("⭐ Overall Genuineness Score", f"{df_repos['overall_genuineness'].iloc[0]:.2f}")

    # ---- Visualization 1: Repo scores ----
    fig_bar = px.bar(df_repos, x="repo", y="score", color="fork", text="genuine_ratio",
                     title="Repository-wise Genuineness Score", labels={"score": "Genuineness Score"})
    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

    # ---- Visualization 2: Commit timeline ----
    st.subheader("📈 Commit Activity Over Time")
    plot_commit_timeline(df_commits)

    # ---- Visualization 3: Commit heatmap ----
    st.subheader("🔥 Contribution Heatmap")
    plot_commit_heatmap(df_commits)

    # ---- Export report ----
    json_report = df_repos.to_json(orient="records", indent=2)
    st.download_button("📥 Download JSON Report", json_report, file_name=f"{username}_report.json", mime="application/json")
