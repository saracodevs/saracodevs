#!/usr/bin/env python3
import os
import json
import math
import urllib.request
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from collections import defaultdict

USERNAME = os.getenv("GITHUB_USERNAME", "saracodevs")
TOKEN = os.getenv("GITHUB_TOKEN")
OUT = Path(os.getenv("OUTPUT_PATH", "assets/github-stats-saracodevs.svg"))

if not TOKEN:
    raise SystemExit("GITHUB_TOKEN não encontrado.")

now = datetime.now(timezone.utc)
year = now.year
start = f"{year}-01-01T00:00:00Z"
end = now.strftime("%Y-%m-%dT%H:%M:%SZ")

query = r'''
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    repositories(
      first: 100,
      ownerAffiliations: OWNER,
      isFork: false,
      privacy: PUBLIC
    ) {
      totalCount
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
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
'''

payload = json.dumps({
    "query": query,
    "variables": {"login": USERNAME, "from": start, "to": end}
}).encode()

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "saracodevs-profile-stats"
    }
)

with urllib.request.urlopen(req) as resp:
    data = json.load(resp)

if "errors" in data:
    raise SystemExit(json.dumps(data["errors"], ensure_ascii=False, indent=2))

user = data["data"]["user"]
calendar = user["contributionsCollection"]["contributionCalendar"]

counts = {}
for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        counts[day["date"]] = day["contributionCount"]

today = now.date()
year_start = date(year, 1, 1)

end_day = today
if counts.get(today.isoformat(), 0) == 0:
    yesterday = today - timedelta(days=1)
    if counts.get(yesterday.isoformat(), 0) > 0:
        end_day = yesterday

current_streak = 0
cursor_day = end_day
while cursor_day >= year_start and counts.get(cursor_day.isoformat(), 0) > 0:
    current_streak += 1
    cursor_day -= timedelta(days=1)

longest_streak = 0
running = 0
cursor_day = year_start
while cursor_day <= today:
    if counts.get(cursor_day.isoformat(), 0) > 0:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0
    cursor_day += timedelta(days=1)

total_contributions = calendar["totalContributions"]
repo_count = user["repositories"]["totalCount"]
followers = user["followers"]["totalCount"]

lang_bytes = defaultdict(int)
lang_colors = {}
for repo in user["repositories"]["nodes"] or []:
    for edge in (repo.get("languages") or {}).get("edges") or []:
        name = edge["node"]["name"]
        lang_bytes[name] += edge["size"]
        lang_colors[name] = edge["node"].get("color") or "#64748B"

total_bytes = sum(lang_bytes.values()) or 1
sorted_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)

primary = sorted_langs[:3]
primary_pct = sum(size / total_bytes * 100 for _, size in primary)
other_pct = max(0.0, 100.0 - primary_pct)

top_langs = [
    (name, size / total_bytes * 100, lang_colors.get(name, "#64748B"))
    for name, size in primary
]

top_langs.append(("Other", other_pct, "#64748B"))

def esc(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

def contribution_color(n):
    if n <= 0:
        return "#101827"
    if n == 1:
        return "#312E81"
    if n == 2:
        return "#4C1D95"
    if n <= 4:
        return "#6D28D9"
    return "#8B5CF6"

svg = []
a = svg.append

a(f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="420" viewBox="0 0 1400 420">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#0B0F15"/>
  <stop offset="1" stop-color="#0A0E14"/>
</linearGradient>
<linearGradient id="purpleLine" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#7C3AED"/>
  <stop offset="1" stop-color="#A78BFA"/>
</linearGradient>
<style>
.cardTitle{{font:700 19px Inter,Segoe UI,Arial,sans-serif;fill:#E5E7EB}}
.label{{font:500 15px Inter,Segoe UI,Arial,sans-serif;fill:#CBD5E1}}
.value{{font:700 22px Inter,Segoe UI,Arial,sans-serif;fill:#F8FAFC}}
.small{{font:500 12px Inter,Segoe UI,Arial,sans-serif;fill:#64748B}}
.quote{{font:700 27px Inter,Segoe UI,Arial,sans-serif;fill:#F8FAFC}}
.quoteAccent{{font:700 27px Inter,Segoe UI,Arial,sans-serif;fill:#9B5CFF}}
.quoteMono{{font:700 14px ui-monospace,SFMono-Regular,Consolas,monospace;fill:#94A3B8;letter-spacing:1.5px}}
.lang{{font:500 16px Inter,Segoe UI,Arial,sans-serif;fill:#D6DCE8}}
.pct{{font:600 16px Inter,Segoe UI,Arial,sans-serif;fill:#AAB3C2}}
</style>
</defs>''')

a('<rect width="1400" height="420" rx="18" fill="url(#bg)"/>')
a('<rect x="1" y="1" width="1398" height="418" rx="17" stroke="#1F2937"/>')

# LEFT — summary metrics
a('<rect x="30" y="30" width="390" height="340" rx="16" fill="#0B1119" stroke="#253041"/>')

rows = [
    ("Total Contributions", total_contributions, "plus"),
    ("Current Streak", current_streak, "fire"),
    ("Longest Streak", longest_streak, "flame"),
    ("Total Repositories", repo_count, "repo"),
    ("Followers", followers, "user"),
]
ys = [65, 120, 175, 230, 285]

for (label, value, kind), y in zip(rows, ys):
    a(f'<g transform="translate(58 {y})"><circle cx="12" cy="12" r="11" fill="#131B2A" stroke="#6D5DFB"/>')
    if kind == "plus":
        a('<path d="M7 12h10M12 7v10" stroke="#9C8CFF" stroke-width="2" stroke-linecap="round"/>')
    elif kind == "fire":
        a('<path d="M12 4c-4 4-5 7-5 10a5 5 0 0 0 10 0c0-3-2-5-5-10z" fill="#8B5CF6"/>')
    elif kind == "flame":
        a('<path d="M8 18c7-2 8-7 8-11-3 2-5 1-6-1-3 4-4 8-2 12z" fill="#A78BFA"/>')
    elif kind == "repo":
        a('<rect x="6" y="7" width="12" height="10" rx="2" stroke="#9C8CFF" stroke-width="1.5"/><path d="M8 10h8M8 13h5" stroke="#9C8CFF" stroke-width="1.5" stroke-linecap="round"/>')
    else:
        a('<circle cx="12" cy="9" r="4" fill="#9C8CFF"/><path d="M5 19c1-5 4-7 7-7s6 2 7 7" stroke="#9C8CFF" stroke-width="2" fill="none" stroke-linecap="round"/>')
    a(f'<text x="38" y="17" class="label">{esc(label)}</text>')
    a(f'<text x="300" y="17" text-anchor="end" class="value">{value}</text></g>')

a('<line x1="58" y1="326" x2="392" y2="326" stroke="#192334"/>')
a(f'<text x="58" y="352" class="small">atualizado automaticamente • {today.strftime("%d/%m/%Y")}</text>')

# CENTER — languages
a('<rect x="445" y="30" width="545" height="340" rx="16" fill="#0B1119" stroke="#253041"/>')
a('<text x="475" y="70" class="cardTitle">Top Languages</text>')
a('<rect x="475" y="100" width="455" height="12" rx="6" fill="#111827"/>')

bar_x, bar_w, bar_cursor = 475, 455, 475
for i, (name, pct, color) in enumerate(top_langs):
    segment = bar_w * (pct / 100)
    radius = 6 if i in (0, len(top_langs)-1) else 0
    a(f'<rect x="{bar_cursor:.1f}" y="100" width="{max(segment,1):.1f}" height="12" rx="{radius}" fill="{color}"/>')
    bar_cursor += segment

for i in range(4):
    y = 155 + i * 48
    if i < len(top_langs):
        name, pct, color = top_langs[i]
        a(f'<circle cx="488" cy="{y}" r="7" fill="{color}"/>')
        a(f'<text x="512" y="{y+6}" class="lang">{esc(name)}</text>')
        a(f'<text x="955" y="{y+6}" text-anchor="end" class="pct">{pct:.1f}%</text>')
    else:
        a(f'<circle cx="488" cy="{y}" r="7" fill="#334155"/>')
        a(f'<text x="512" y="{y+6}" class="lang">—</text>')

# RIGHT — quote card
a('<rect x="1015" y="30" width="355" height="340" rx="16" fill="#0B1119" stroke="#7C3AED" stroke-width="2"/>')
a('<text x="1050" y="105" class="quote">“Em constante</text>')
a('<text x="1050" y="145" class="quoteAccent">evolução.”</text>')
a('<line x1="1050" y1="180" x2="1125" y2="180" stroke="#8B5CF6" stroke-width="2"/>')
a('<text x="1050" y="235" class="quoteMono">MESMO PROCESSO.</text>')
a('<text x="1050" y="265" class="quoteMono">MAIS RESULTADO.</text>')
a('<text x="1335" y="330" text-anchor="end" style="font:700 20px ui-monospace,Consolas,monospace;fill:#8B5CF6;">&lt;/&gt;</text>')

a('<line x1="30" y1="395" x2="1370" y2="395" stroke="#202938"/>')
a('<line x1="30" y1="395" x2="160" y2="395" stroke="url(#purpleLine)" stroke-width="2"/>')
a('</svg>')

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(svg), encoding="utf-8")
print(f"SVG atualizado: {OUT}")
