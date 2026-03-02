"""
scrape_criterion.py
─────────────────────────────────────────────────────────────────────────────
Scrapes Criterion Collection films from criterion.com and matches them
to IMDb IDs for integration with our recommendation system.

USAGE:
  python scrape_criterion.py

REQUIREMENTS:
  pip install requests beautifulsoup4 python-dotenv
─────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
OUTPUT_FILE = "criterion_films.json"

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

print("🎬 Scraping Criterion Collection from criterion.com...\n")

criterion_films = {}
page = 1
max_pages = 50  # Safety limit

while page <= max_pages:
    try:
        # Fetch Criterion shop page
        url = f"https://www.criterion.com/shop/browse/list?sort=spine_number&page={page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Find all film entries
        films = soup.find_all('div', class_='product')
        
        if not films:
            print(f"📄 Page {page}: No films found. Stopping.")
            break
        
        print(f"📄 Page {page}: Found {len(films)} films")
        
        for film in films:
            try:
                # Get title
                title_elem = film.find('a', class_='product_title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                film_url = title_elem.get('href', '')
                
                # Get spine number
                spine_elem = film.find('span', class_='spine_number')
                spine = spine_elem.get_text(strip=True) if spine_elem else "Unknown"
                
                # Search TMDB for IMDb ID
                search_r = requests.get(
                    "https://api.themoviedb.org/3/search/movie",
                    params={"api_key": TMDB_API_KEY, "query": title},
                    timeout=5
                )
                search_results = search_r.json().get("results", [])
                
                imdb_id = None
                if search_results:
                    # Get IMDb ID from first result
                    tmdb_id = search_results[0]['id']
                    detail_r = requests.get(
                        f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                        params={"api_key": TMDB_API_KEY},
                        timeout=5
                    )
                    imdb_id = detail_r.json().get("imdb_id")
                
                if imdb_id:
                    criterion_films[imdb_id] = {
                        "title": title,
                        "spine": spine,
                        "criterion_url": film_url,
                    }
                    print(f"  ✅ {spine}: {title} ({imdb_id})")
                else:
                    print(f"  ⚠️  {spine}: {title} (no IMDb ID found)")
                
                time.sleep(0.2)  # Be polite to API
                
            except Exception as e:
                print(f"  ❌ Error processing film: {e}")
                continue
        
        page += 1
        time.sleep(1)  # Be polite to criterion.com
        
    except Exception as e:
        print(f"❌ Error fetching page {page}: {e}")
        break

# Save to JSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(criterion_films, f, indent=2)

print(f"\n✅ Saved {len(criterion_films)} Criterion films to {OUTPUT_FILE}")
print(f"📊 Sample: {list(criterion_films.items())[:3]}")
