import json
import os
import urllib.request
import urllib.parse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
picks_file = os.path.join(ROOT_DIR, "catalogs", "antigravity_picks.json")

with open(picks_file, "r", encoding="utf-8") as f:
    picks = json.load(f)

for p in picks:
    mid = p["id"]
    name = p["name"]
    print(f"Checking {name} ({mid})...")
    q = urllib.parse.quote(name)
    url = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={q}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            metas = data.get("metas", [])
            if metas:
                m = metas[0]
                p["id"] = m.get("id", mid)
                p["genres"] = m.get("genres", [])
                p["year"] = str(m.get("year") or p.get("year", ""))
                p["imdbRating"] = str(m.get("imdbRating", ""))
                print(f"  -> Found {p['id']}, genres: {p['genres']}")
            else:
                print("  -> No match, checking fallback")
    except Exception as e:
        print(f"  -> Error: {e}")

manual_genres = {
    "Nobody 2": ["Action", "Crime", "Thriller"],
    "The Strangers: Chapter 2": ["Horror", "Mystery", "Thriller"],
    "Borderline": ["Comedy", "Thriller"],
    "Die My Love": ["Comedy", "Drama", "Horror"],
    "The Conjuring: Last Rites": ["Horror", "Mystery", "Thriller"],
    "Eden": ["Drama", "Thriller"],
    "Dirty Angels": ["Action", "Drama", "War"],
    "One Battle After Another": ["Action", "Adventure", "Drama"],
    "Weapons": ["Horror", "Mystery"],
    "The Order": ["Crime", "Drama", "Thriller"]
}

for p in picks:
    if not p.get("genres") or len(p["genres"]) == 0:
        if p["name"] in manual_genres:
            p["genres"] = manual_genres[p["name"]]
            print(f"  -> Applied fallback genres for {p['name']}: {p['genres']}")

with open(picks_file, "w", encoding="utf-8") as f:
    json.dump(picks, f, indent=2)

print("Finished enriching antigravity_picks.json")
