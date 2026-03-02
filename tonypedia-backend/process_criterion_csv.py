"""
process_criterion_csv.py
─────────────────────────────────────────────────────────────────────────────
Converts Criterion movies CSV to criterion_films.json
by matching titles to IMDb IDs via TMDB API.

CSV format: ,Title,Description,Director,Country,Year,Language,Image

USAGE:
  1. Ensure data.csv is in this directory
  2. Run: python process_criterion_csv.py

This will create criterion_films.json with ~1200+ Criterion films
─────────────────────────────────────────────────────────────────────────────
"""

import os
import csv
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = "data.csv"
OUTPUT_FILE = "criterion_films.json"
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

if not os.path.exists(INPUT_FILE):
    print(f"❌ {INPUT_FILE} not found")
    exit(1)

print(f"🎬 Processing Criterion Collection from {INPUT_FILE}...\n")

criterion_films = {}
failed = []
matched = 0
skipped = 0

try:
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader, 1):
            title = row.get('Title', '').strip()
            year = row.get('Year', '').strip()
            director = row.get('Director', '').strip()
            
            if not title:
                skipped += 1
                continue
            
            # Search TMDB for the film
            search_query = f"{title} {year}" if year else title
            
            try:
                search_r = requests.get(
                    "https://api.themoviedb.org/3/search/movie",
                    params={
                        "api_key": TMDB_API_KEY,
                        "query": search_query,
                        "year": year if year else None
                    },
                    timeout=5
                )
                
                results = search_r.json().get("results", [])
                
                if not results:
                    # Retry without year if not found
                    if year:
                        search_r = requests.get(
                            "https://api.themoviedb.org/3/search/movie",
                            params={"api_key": TMDB_API_KEY, "query": title},
                            timeout=5
                        )
                        results = search_r.json().get("results", [])
                
                if results:
                    # Get best match (first result)
                    best_match = results[0]
                    tmdb_id = best_match['id']
                    
                    # Fetch IMDb ID
                    detail_r = requests.get(
                        f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                        params={"api_key": TMDB_API_KEY},
                        timeout=5
                    )
                    
                    imdb_id = detail_r.json().get("imdb_id")
                    
                    if imdb_id:
                        criterion_films[imdb_id] = {
                            "title": title,
                            "year": year,
                            "director": director,
                            "spine_number": idx,
                        }
                        matched += 1
                        
                        if matched % 50 == 0:
                            print(f"✅ Matched {matched} films...")
                    else:
                        failed.append((idx, title, "No IMDb ID"))
                else:
                    failed.append((idx, title, "Not found on TMDB"))
                
                time.sleep(0.15)  # Be polite to API (max ~6-7 requests/second)
                
            except Exception as e:
                failed.append((idx, title, str(e)))
                continue
        
except Exception as e:
    print(f"❌ Error reading CSV: {e}")
    exit(1)

# Save to JSON
with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
    json.dump(criterion_films, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"✅ SUCCESS")
print(f"{'='*60}")
print(f"📊 Matched: {matched} films")
print(f"⚠️  Failed: {len(failed)} films")
print(f"⏭️  Skipped: {skipped} films")
print(f"\n💾 Saved to: {OUTPUT_FILE}")

if failed and len(failed) <= 20:
    print(f"\n❌ Failed matches (first 20):")
    for spine, title, reason in failed[:20]:
        print(f"  #{spine}: {title} - {reason}")

print(f"\n📊 Sample matches:")
for imdb_id, data in list(criterion_films.items())[:5]:
    print(f"  {imdb_id}: {data['title']} ({data['year']}) by {data['director']}")
