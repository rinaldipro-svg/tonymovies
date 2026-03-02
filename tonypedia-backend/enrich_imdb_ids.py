"""
enrich_imdb_ids.py
─────────────────────────────────────────────────────────────────────────────
Enriches movie_data.pkl with IMDb IDs by looking them up on TMDB.
This allows the recommendation engine to fetch ratings and posters.

USAGE:
  python enrich_imdb_ids.py

REQUIREMENTS:
  pip install requests python-dotenv
─────────────────────────────────────────────────────────────────────────────
"""

import os
import pickle
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
MOVIE_DATA_FILE = "movie_data.pkl"
OUTPUT_FILE = "movie_data_enriched.pkl"

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

print(f"📂 Loading {MOVIE_DATA_FILE}...")
with open(MOVIE_DATA_FILE, "rb") as f:
    movie_data = pickle.load(f)

print(f"🎬 Found {len(movie_data)} movies to enrich\n")

enriched = 0
skipped = 0
errors = 0

for movie_id, movie_info in list(movie_data.items()):
    title = movie_info.get("title", "Unknown")
    year = movie_info.get("year", "")
    
    # Skip if already has IMDb ID
    if movie_info.get("imdb_id"):
        skipped += 1
        continue
    
    # Search TMDB by title
    try:
        search_query = f"{title} {year}".strip()
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_API_KEY, "query": search_query, "include_adult": False},
            timeout=5
        )
        results = r.json().get("results", [])
        
        if not results:
            print(f"⚠️  Not found on TMDB: {title} ({year})")
            errors += 1
            time.sleep(0.2)
            continue
        
        # Use first result
        tmdb_result = results[0]
        tmdb_id = tmdb_result["id"]
        
        # Fetch IMDb ID for this TMDB movie
        detail_r = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY},
            timeout=5
        )
        imdb_id = detail_r.json().get("imdb_id", "")
        
        if imdb_id:
            movie_data[movie_id]["imdb_id"] = imdb_id
            enriched += 1
            print(f"✅ {title} ({year}) → {imdb_id}")
        else:
            print(f"⚠️  No IMDb ID found for {title}")
            errors += 1
        
        time.sleep(0.2)  # Be polite to API
        
    except Exception as e:
        print(f"❌ Error enriching {title}: {e}")
        errors += 1
        time.sleep(0.2)

# Save enriched data
print(f"\n💾 Saving enriched data to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(movie_data, f)

print(f"\n✅ Complete!")
print(f"   {enriched} movies enriched with IMDb IDs")
print(f"   {skipped} movies already had IMDb IDs")
print(f"   {errors} errors/not found")
print(f"\n📝 Next step: Replace movie_data.pkl with {OUTPUT_FILE}")
print(f"   mv {OUTPUT_FILE} {MOVIE_DATA_FILE}")
