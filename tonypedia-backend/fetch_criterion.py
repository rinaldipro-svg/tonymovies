"""
fetch_criterion.py
─────────────────────────────────────────────────────────────────────────────
Fetches Criterion Collection films from TMDB and saves to a JSON file.
The Criterion Collection has a collection ID on TMDB that we can query.

USAGE:
  python fetch_criterion.py

REQUIREMENTS:
  pip install requests python-dotenv
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OUTPUT_FILE = "criterion_films.json"

# Criterion Collection ID on TMDB
CRITERION_COLLECTION_ID = 31643

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

print(f"🎬 Fetching Criterion Collection films from TMDB...\n")

criterion_films = {}
page = 1
total_pages = 1

while page <= total_pages:
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/collection/{CRITERION_COLLECTION_ID}",
            params={
                "api_key": TMDB_API_KEY,
                "page": page,
                "sort_by": "primary_release_date.desc"
            },
            timeout=10
        )
        data = r.json()
        
        if "parts" not in data:
            print(f"⚠️  No films found or invalid collection ID")
            break
        
        total_pages = data.get("total_pages", 1)
        print(f"📄 Page {page}/{total_pages}")
        
        for film in data.get("parts", []):
            imdb_id = film.get("external_ids", {}).get("imdb_id")
            if not imdb_id:
                # Try to fetch external IDs
                ext_r = requests.get(
                    f"https://api.themoviedb.org/3/movie/{film['id']}/external_ids",
                    params={"api_key": TMDB_API_KEY},
                    timeout=5
                )
                imdb_id = ext_r.json().get("imdb_id")
            
            if imdb_id:
                criterion_films[imdb_id] = {
                    "title": film.get("title"),
                    "year": film.get("release_date", "")[:4],
                    "tmdb_id": film.get("id"),
                    "imdb_id": imdb_id,
                }
                print(f"  ✅ {film.get('title')} ({imdb_id})")
            
            time.sleep(0.1)  # Be polite to API
        
        page += 1
        
    except Exception as e:
        print(f"❌ Error fetching page {page}: {e}")
        break

# Save to JSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(criterion_films, f, indent=2)

print(f"\n✅ Saved {len(criterion_films)} Criterion films to {OUTPUT_FILE}")
