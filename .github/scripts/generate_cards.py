"""Generate README SVG cards from the GitHub public API (standard library only)."""

import argparse
from collections import Counter
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
THEMES = {
    "dark": ("#0d1117", "#30363d", "#e6edf3", "#8b949e", "#58a6ff"),
    "light": ("#ffffff", "#d0d7de", "#1f2328", "#656d76", "#0969da"),
}


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def card(title, subtitle, rows, theme, total=None):
    background, border, text, muted, accent = THEMES[theme]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="280" viewBox="0 0 480 280" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(subtitle + ". " + "; ".join(f"{label}: {value}" for label, value in rows))}</desc>',
        f'<rect x="0.5" y="0.5" width="479" height="279" rx="12" fill="{background}" stroke="{border}"/>',
        '<g font-family="Segoe UI, Ubuntu, sans-serif">',
        f'<text x="24" y="38" fill="{accent}" font-size="20" font-weight="600">{escape(title)}</text>',
        f'<text x="24" y="62" fill="{muted}" font-size="12">{escape(subtitle)}</text>',
    ]
    for index, (label, value) in enumerate(rows):
        y = 96 + index * 29
        parts.extend([
            f'<text x="24" y="{y}" fill="{text}" font-size="14">{escape(label)}</text>',
            f'<text x="456" y="{y}" text-anchor="end" fill="{text}" font-size="14" font-weight="600">{value:,}</text>',
        ])
        if total:
            width = 200 * value / total
            parts.append(f'<rect x="220" y="{y - 9}" width="{width:.2f}" height="8" rx="4" fill="{accent}"/>')
    if not rows:
        parts.append(f'<text x="24" y="105" fill="{muted}" font-size="14">No repository languages yet.</text>')
    parts.append('</g></svg>\n')
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "dev-khoi"))
    args = parser.parse_args()
    username = quote(args.username, safe="")
    user = api(f"/users/{username}")
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{username}/repos?type=owner&per_page=100&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    original = [repo for repo in repos if not repo["fork"]]
    languages = Counter(repo["language"] for repo in original if repo["language"])
    top_languages = sorted(languages.items(), key=lambda item: (-item[1], item[0]))[:6]
    stats = [
        ("Public repositories", len(repos)),
        ("Original repositories", len(original)),
        ("Stars earned", sum(repo["stargazers_count"] for repo in original)),
        ("Forks of your repositories", sum(repo["forks_count"] for repo in original)),
        ("Followers", user["followers"]),
        ("Following", user["following"]),
    ]
    output = ROOT / "cards"
    output.mkdir(exist_ok=True)
    for theme in THEMES:
        (output / f"stats-{theme}.svg").write_text(
            card("GitHub Stats", f"@{user['login']} · Public GitHub activity", stats, theme), encoding="utf-8"
        )
        (output / f"languages-{theme}.svg").write_text(
            card("Languages by Repo Count", "Primary language · Public non-fork repositories", top_languages, theme, sum(languages.values())),
            encoding="utf-8",
        )
    print(f"Generated four SVG cards for {user['login']} from {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
