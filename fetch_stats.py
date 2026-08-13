#!/usr/bin/env python3
"""
拉取 GitHub 统计数据 → assets/generated/stats.json
供 generator.py 绘制自绘统计卡与仓库卡(零外部依赖,不依赖 github-readme-stats 等服务)。

用法:
    python3 fetch_stats.py                # 未认证(60 次/小时,够用)
    GITHUB_TOKEN=xxx python3 fetch_stats.py   # 认证(5000 次/小时,CI 里用)
"""

import json
import os
import urllib.request
import datetime

USER = "CraneBW"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "generated", "stats.json")


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "crane-profile-bot",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&sort=updated")

    stars = sum(r["stargazers_count"] for r in repos)
    forks = sum(r["forks_count"] for r in repos)

    # 语言占比(按字节)
    lang_bytes = {}
    for r in repos:
        try:
            langs = api(f"/repos/{USER}/{r['name']}/languages")
        except Exception:
            continue
        for lang, n in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + n

    # 近一年提交数(搜索 API,需 cloak preview header)
    year_commits = 0
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    try:
        req = urllib.request.Request(
            f"https://api.github.com/search/commits?q=author:{USER}+committer-date:>{since}&per_page=1",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "crane-profile-bot",
                **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            year_commits = json.load(r)["total_count"]
    except Exception:
        pass

    # 精选仓库(排除同名 profile 仓库;star 优先,其次有描述,再按最近更新)
    candidates = [r for r in repos if r["name"] != USER]
    candidates.sort(
        key=lambda r: (r["stargazers_count"], bool(r["description"]), r["pushed_at"]),
        reverse=True,
    )
    featured = [
        {
            "name": r["name"],
            "description": (r["description"] or "")[:60],
            "language": r["language"],
            "stars": r["stargazers_count"],
        }
        for r in candidates[:3]
    ]

    data = {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "following": user["following"],
        "gists": user["public_gists"],
        "stars": stars,
        "forks": forks,
        "year_commits": year_commits,
        "languages": lang_bytes,
        "featured_repos": featured,
        "updated_at": datetime.date.today().isoformat(),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✓ stats.json 更新完成:")
    print(json.dumps({k: v for k, v in data.items() if k != "languages"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
