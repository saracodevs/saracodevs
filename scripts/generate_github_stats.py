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
top = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:4]
top_langs = [
    (name, size / total_bytes * 100, lang_colors.get(name, "#64748B"))
    for name, size in top
]

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

a('<svg width="1400" height="525" viewBox="0 0 1400 525" fill="none" xmlns="http://www.w3.org/2000/svg">')
a('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1400" y2="525">
  <stop stop-color="#0D1117"/>
  <stop offset="1" stop-color="#090D13"/>
</linearGradient>
<linearGradient id="purpleLine" x1="0" y1="0" x2="1" y2="1">
  <stop stop-color="#7C3AED"/>
  <stop offset="1" stop-color="#A78BFA"/>
</linearGradient>
<style>
.title{font:700 22px Inter,Segoe UI,Arial,sans-serif;fill:#F8FAFC}
.cardTitle{font:700 18px Inter,Segoe UI,Arial,sans-serif;fill:#E5E7EB}
.label{font:500 15px Inter,Segoe UI,Arial,sans-serif;fill:#CBD5E1}
.value{font:700 22px Inter,Segoe UI,Arial,sans-serif;fill:#F8FAFC}
.small{font:500 12px Inter,Segoe UI,Arial,sans-serif;fill:#64748B}
.quote{font:600 22px Inter,Segoe UI,Arial,sans-serif;fill:#B8A1FF}
.mono{font:600 10px ui-monospace,SFMono-Regular,Consolas,monospace;fill:#7C83A6;letter-spacing:1px}
.lang{font:500 14px Inter,Segoe UI,Arial,sans-serif;fill:#D6DCE8}
.pct{font:500 14px Inter,Segoe UI,Arial,sans-serif;fill:#AAB3C2}
</style>
</defs>''')

a('<rect width="1400" height="525" rx="18" fill="url(#bg)"/>')
a('<rect x="1" y="1" width="1398" height="523" rx="17" stroke="#1F2937"/>')
a('<rect x="28" y="28" width="20" height="16" rx="4" fill="#7C3AED"/>')
a('<circle cx="38" cy="36" r="3" fill="#C4B5FD"/>')
a('<text x="62" y="43" class="title">GitHub Stats</text>')
a('<line x1="190" y1="36" x2="1278" y2="36" stroke="#202938"/>')
a('<text x="1292" y="41" class="mono">//</text>')

a('<rect x="30" y="80" width="390" height="390" rx="16" fill="#0B1119" stroke="#253041"/>')

rows = [
    ("Total Contributions", total_contributions, "plus"),
    ("Current Streak", current_streak, "fire"),
    ("Longest Streak", longest_streak, "flame"),
    ("Total Repositories", repo_count, "repo"),
    ("Followers", followers, "user"),
]
ys = [120, 180, 240, 300, 360]

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

a('<line x1="58" y1="415" x2="392" y2="415" stroke="#192334"/>')
a(f'<text x="58" y="445" class="small">atualizado automaticamente • {today.strftime("%d/%m/%Y")}</text>')

a('<rect x="445" y="80" width="925" height="220" rx="16" fill="#0B1119" stroke="#253041"/>')
a(f'<text x="470" y="112" class="cardTitle">Contributions ({year})</text>')

jan1 = date(year, 1, 1)
dec31 = date(year, 12, 31)
grid_start = jan1 - timedelta(days=(jan1.weekday() + 1) % 7)
weeks = math.ceil(((dec31 - grid_start).days + 1) / 7)

grid_x, grid_y, gap, size = 520, 160, 14, 10
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

for month in range(1, 13):
    first = date(year, month, 1)
    week_idx = (first - grid_start).days // 7
    x = grid_x + week_idx * gap
    a(f'<text x="{x}" y="145" class="small">{months[month-1]}</text>')

for label, row in [("Mon",1),("Wed",3),("Fri",5)]:
    a(f'<text x="470" y="{grid_y + row*gap + 9}" class="small">{label}</text>')

for week_index in range(weeks):
    for row_index in range(7):
        day = grid_start + timedelta(days=week_index * 7 + row_index)
        if day.year != year or day > today:
            fill, opacity = "#0D1420", "0.35"
        else:
            fill, opacity = contribution_color(counts.get(day.isoformat(), 0)), "1"
        x = grid_x + week_index * gap
        y = grid_y + row_index * gap
        a(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{fill}" opacity="{opacity}"/>')

a('<g transform="translate(1215 278)"><text x="-42" y="0" class="small">Less</text>')
for i, color in enumerate(["#101827","#312E81","#4C1D95","#6D28D9","#8B5CF6"]):
    a(f'<rect x="{i*15}" y="-10" width="10" height="10" rx="2" fill="{color}"/>')
a('<text x="82" y="0" class="small">More</text></g>')

a('<rect x="445" y="325" width="545" height="145" rx="16" fill="#0B1119" stroke="#253041"/>')
a('<text x="470" y="358" class="cardTitle">Top Languages</text>')
a('<rect x="470" y="378" width="450" height="9" rx="5" fill="#111827"/>')

bar_x, bar_w, bar_cursor = 470, 450, 470
for i, (name, pct, color) in enumerate(top_langs):
    segment = bar_w * (pct / 100)
    radius = 5 if i in (0, len(top_langs)-1) else 0
    a(f'<rect x="{bar_cursor:.1f}" y="378" width="{max(segment,1):.1f}" height="10" rx="{radius}" fill="{color}"/>')
    bar_cursor += segment

for i in range(4):
    y = 410 + i * 24
    if i < len(top_langs):
        name, pct, color = top_langs[i]
        a(f'<circle cx="480" cy="{y}" r="6" fill="{color}"/>')
        a(f'<text x="498" y="{y+5}" class="lang">{esc(name)}</text>')
        a(f'<text x="945" y="{y+5}" text-anchor="end" class="pct">{pct:.1f}%</text>')
    else:
        a(f'<circle cx="480" cy="{y}" r="6" fill="#334155"/>')
        a(f'<text x="498" y="{y+5}" class="lang">—</text>')

a('<rect x="1015" y="325" width="355" height="145" rx="16" fill="#0B1119" stroke="#253041"/>')
a('<text x="1045" y="372" class="quote">“Em constante</text>')
a('<text x="1045" y="400" class="quote">evolução.”</text>')
a('<text x="1045" y="434" class="mono">MESMO PROCESSO.</text>')
a('<text x="1045" y="451" class="mono">MAIS RESULTADO.</text>')
a('<text x="1335" y="452" text-anchor="end" style="font:700 16px ui-monospace,Consolas,monospace;fill:#8B5CF6;">&lt;/&gt;</text>')

a('<line x1="30" y1="495" x2="1370" y2="495" stroke="#202938"/>')
a('<line x1="30" y1="495" x2="150" y2="495" stroke="url(#purpleLine)" stroke-width="2"/>')
a('</svg>')

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(svg), encoding="utf-8")
print(f"SVG atualizado: {OUT}")
