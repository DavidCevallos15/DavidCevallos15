"""Generate GitHub profile cards from public REST data. Python standard library only."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USERNAME = os.environ.get("PROFILE_USERNAME", "DavidCevallos15")
COLORS = ["#73e2c4", "#8cbcff", "#c3a6ff", "#f1c979", "#f29eaf", "#9caabc"]


def api(path):
    headers = {"User-Agent": "DavidCevallos15-profile", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com/{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def text(x, y, value, size=16, color="#e9f1f5", weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'


def svg(title, height, content):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img">'
            f'<title>{escape(title)}</title><g font-family="Segoe UI,Arial,sans-serif">'
            f'<rect x="1" y="1" width="958" height="{height - 2}" rx="18" fill="#0d1722" stroke="#273847"/>'
            f'{content}</g></svg>\n')


def build_cards(user, repos, now):
    own = [r for r in repos if not r.get("fork") and not r.get("private")]
    cutoff = now - timedelta(days=90)
    active = sum(bool(r.get("pushed_at")) and datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) >= cutoff for r in own)
    stamp = now.strftime("%Y-%m-%d · UTC")
    stats = [(len(own), "Repos propios públicos"), (sum(r.get("stargazers_count", 0) for r in own), "Estrellas recibidas"),
             (user["followers"], "Seguidores"), (active, "Repos con push / 90 días")]
    body = text(32, 38, "EL TALLER / ACTIVIDAD PÚBLICA", 13, "#73e2c4", 600)
    body += text(928, 38, "", 12)
    for i, (value, label) in enumerate(stats):
        x = 32 + i * 232
        if i:
            body += f'<path d="M{x - 18} 66V154" stroke="#273847"/>'
        body += text(x, 111, value, 42, "#e9f1f5", 650)
        body += text(x, 143, label, 14, "#a9bac7")
    body += text(32, 190, f"GitHub REST API · Sin forks · Actualizado {stamp}", 12, "#a9bac7")
    activity = svg("Actividad pública de " + USERNAME, 214, body)

    counts = Counter(r.get("language") or "Sin clasificar" for r in own)
    groups = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if len(groups) > 6:
        groups = groups[:5] + [("Otros", sum(count for _, count in groups[5:]))]
    body = text(32, 38, "LENGUAJES / REPOSITORIOS PROPIOS", 13, "#73e2c4", 600)
    body += text(32, 66, "Distribución por lenguaje principal de cada repositorio", 17, "#e9f1f5", 500)
    start = 32.0
    for i, (label, count) in enumerate(groups):
        width = count / max(1, len(own)) * 896
        body += f'<rect x="{start:.2f}" y="88" width="{width:.2f}" height="10" fill="{COLORS[i]}"/>'
        start += width
        x, y = 32 + (i % 3) * 302, 133 + (i // 3) * 35
        body += f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{COLORS[i]}"/>'
        body += text(x + 20, y, f"{label} · {count} ({count / max(1, len(own)):.0%})", 15, "#cbd9e2")
    if not groups:
        body += text(32, 133, "Todavía no hay repositorios públicos propios.", 15, "#a9bac7")
    body += text(32, 206, f"No mide líneas de código ni nivel de dominio · Actualizado {stamp}", 12, "#a9bac7")
    return {"activity.svg": activity, "languages.svg": svg("Lenguajes principales de repositorios públicos", 232, body)}


def main():
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", USERNAME):
        raise ValueError("Invalid GitHub username")
    user, repos, page = api(f"users/{USERNAME}"), [], 1
    while True:
        batch = api(f"users/{USERNAME}/repos?per_page=100&type=owner&page={page}")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    # Fetch and render everything before replacing any saved card.
    cards = build_cards(user, repos, datetime.now(timezone.utc))
    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name, content in cards.items():
        temporary = assets / (name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(assets / name)
    print(f"Updated {len(cards)} cards for {USERNAME}; inspected {len(repos)} public repositories.")


if __name__ == "__main__":
    main()
