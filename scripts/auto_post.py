import os
import re
import json
import datetime
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"

def get_latest_race():
    resp = requests.get("https://api.jolpi.ca/ergast/f1/current/last/results.json")
    resp.raise_for_status()
    data = resp.json()
    race = data["MRData"]["RaceTable"]["Races"][0]
    return race

def get_driver_standings():
    resp = requests.get("https://api.jolpi.ca/ergast/f1/current/driverStandings.json")
    resp.raise_for_status()
    data = resp.json()
    standings = data["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    return standings[:10]

def generate_post_text(race, standings):
    race_name = race["raceName"]
    winner = race["Results"][0]["Driver"]
    winner_name = f"{winner['givenName']} {winner['familyName']}"
    team = race["Results"][0]["Constructor"]["name"]
    top3 = race["Results"][:3]
    top3_text = "\n".join(
        f"{r['position']}. {r['Driver']['givenName']} {r['Driver']['familyName']} ({r['Constructor']['name']})"
        for r in top3
    )

    prompt = f"""You are writing a blog post for an F1 fan blog called "Slipstream F1".
Write a factual, engaging race recap based ONLY on this verified data — do not invent
any facts, times, or events not listed below.

Race: {race_name}
Winner: {winner_name} ({team})
Top 3:
{top3_text}

Write 400-600 words. Include a short intro, a summary of the top 3, and a brief closing
thought about championship implications. Do not use markdown headers. Return plain
paragraphs only."""

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(GEMINI_URL, json=body)
    resp.raise_for_status()
    result = resp.json()
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return text, race_name

def generate_standings_chart(standings, slug):
    labels = [f"{s['Driver']['familyName']}" for s in standings]
    points = [float(s["points"]) for s in standings]

    chart_config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{"label": "Points", "data": points}]
        },
        "options": {
            "title": {"display": True, "text": "Driver Standings"}
        }
    }

    url = "https://quickchart.io/chart"
    params = {"c": json.dumps(chart_config), "width": 800, "height": 400}
    resp = requests.get(url, params=params)
    resp.raise_for_status()

    image_path = f"static/images/{slug}.png"
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    with open(image_path, "wb") as f:
        f.write(resp.content)
    return f"images/{slug}.png"

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def main():
    race = get_latest_race()
    standings = get_driver_standings()

    post_text, race_name = generate_post_text(race, standings)
    slug = slugify(race_name) + "-" + datetime.date.today().isoformat()

    image_rel_path = generate_standings_chart(standings, slug)

    now = datetime.datetime.now().isoformat()
    frontmatter = f"""+++
date = '{now}'
draft = true
title = '{race_name} Recap'
cover = {{ image = "{image_rel_path}" }}
+++

"""

    post_path = f"content/posts/{slug}.md"
    os.makedirs(os.path.dirname(post_path), exist_ok=True)
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + post_text)

    print(f"Created {post_path} and {image_rel_path}")

if __name__ == "__main__":
    main()