"""
tonypedia_populate.py
─────────────────────────────────────────────────────────────────────────────
Auto-populates tonypedia.csv with imdb_id, title, year, and a TMDB baseline
score. You only need to manually fill in:
  - score       → your personal Tonypedia rating (0.0 – 10.0)
  - notes       → your editorial one-liner

USAGE:
  1. Add your movie titles to the MOVIES list below (one per line)
  2. Run: python tonypedia_populate.py
  3. Open the generated tonypedia.csv and fill in score + notes columns
  4. Upload via the /admin/ratings/upload endpoint

REQUIREMENTS:
  pip install requests python-dotenv
─────────────────────────────────────────────────────────────────────────────
"""

import os
import csv
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OUTPUT_FILE  = "tonypedia.csv"

# ──────────────────────────────────────────────────────────────────────────────
# ADD YOUR MOVIES HERE — just the title, the script handles the rest
# ──────────────────────────────────────────────────────────────────────────────
MOVIES = [
    "Interstellar",
    "The Matrix",
    "Inception",
    "Charlie and the Chocolate Factory",
    "The Shawshank Redemption",
    "Pulp Fiction",
    "The Dark Knight",
    "Schindler's List",
    "Fight Club",
    "Forrest Gump",
    # Add as many as you want below this line...
]
# ──────────────────────────────────────────────────────────────────────────────


def search_movie(title: str) -> dict | None:
    """Search TMDB for a movie title and return its metadata."""
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_API_KEY, "query": title, "include_adult": False},
            timeout=5
        )
        results = r.json().get("results", [])
        if not results:
            return None
        # Take the first (most relevant) result
        return results[0]
    except Exception as e:
        print(f"   ❌ TMDB search error for '{title}': {e}")
        return None


def get_imdb_id(tmdb_id: int) -> str:
    """Fetch the IMDb ID for a given TMDB movie ID."""
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY},
            timeout=5
        )
        return r.json().get("imdb_id", "")
    except Exception as e:
        print(f"   ❌ IMDb ID fetch error for TMDB {tmdb_id}: {e}")
        return ""


def main():
    if not TMDB_API_KEY:
        print("❌ TMDB_API_KEY not found in .env — add it and retry.")
        return

    print(f"🎬 Looking up {len(MOVIES)} movies on TMDB...\n")

    # Load existing CSV to avoid overwriting entries you've already scored
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["imdb_id"]] = row
        print(f"📂 Found existing {OUTPUT_FILE} with {len(existing)} entries — will merge.\n")

    rows = []
    for title in MOVIES:
        print(f"   Searching: {title}")

        tmdb_result = search_movie(title)
        if not tmdb_result:
            print(f"   ⚠️  Not found on TMDB — skipping '{title}'")
            rows.append({
                "imdb_id": "NOT_FOUND",
                "score":   "",
                "notes":   "",
                "title":   title,
                "year":    "",
                "tmdb_score": "",
            })
            time.sleep(0.3)
            continue

        tmdb_id    = tmdb_result["id"]
        found_title = tmdb_result.get("title", title)
        year       = str(tmdb_result.get("release_date", ""))[:4]
        tmdb_score = tmdb_result.get("vote_average", "")

        imdb_id = get_imdb_id(tmdb_id)

        # If this film already exists in the CSV, preserve the score + notes
        if imdb_id and imdb_id in existing:
            preserved_score = existing[imdb_id]["score"]
            preserved_notes = existing[imdb_id]["notes"]
            print(f"   ✅ {found_title} ({year}) → {imdb_id} [existing entry preserved]")
        else:
            preserved_score = ""   # Leave blank for you to fill in
            preserved_notes = ""   # Leave blank for you to fill in
            print(f"   ✅ {found_title} ({year}) → {imdb_id} | TMDB score: {tmdb_score}")

        rows.append({
            "imdb_id":    imdb_id,
            "score":      preserved_score,   # ← YOU fill this in (0.0–10.0)
            "notes":      preserved_notes,   # ← YOU fill this in
            "title":      found_title,        # for your reference only
            "year":       year,               # for your reference only
            "tmdb_score": tmdb_score,         # TMDB baseline for your reference
        })

        time.sleep(0.3)  # Be polite to TMDB API

    # Write output
    fieldnames = ["imdb_id", "score", "notes", "title", "year", "tmdb_score"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    filled   = sum(1 for r in rows if r["score"])
    unfilled = sum(1 for r in rows if not r["score"])

    print(f"\n✅ Saved {len(rows)} movies to {OUTPUT_FILE}")
    print(f"   {filled} entries already scored")
    print(f"   {unfilled} entries waiting for your score + notes")
    print(f"\n📝 Next steps:")
    print(f"   1. Open {OUTPUT_FILE} in Excel or any text editor")
    print(f"   2. Fill in the 'score' column (0.0–10.0) for each film")
    print(f"   3. Fill in the 'notes' column with your one-liner editorial")
    print(f"   4. Upload via POST /admin/ratings/upload when ready")


if __name__ == "__main__":
    main()
