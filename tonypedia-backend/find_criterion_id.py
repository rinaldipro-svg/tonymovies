import os
import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not TMDB_API_KEY:
    print("❌ TMDB_API_KEY not found in .env")
    exit(1)

# Search for Criterion Collection
r = requests.get(
    "https://api.themoviedb.org/3/search/collection",
    params={"api_key": TMDB_API_KEY, "query": "Criterion Collection"},
    timeout=10
)

results = r.json().get("results", [])
print("🎬 Criterion Collection search results:\n")

if not results:
    print("No results found. Trying alternative searches...\n")
    
    # Try alternative searches
    for query in ["Criterion", "The Criterion Collection", "Criterion Films"]:
        r = requests.get(
            "https://api.themoviedb.org/3/search/collection",
            params={"api_key": TMDB_API_KEY, "query": query},
            timeout=10
        )
        results = r.json().get("results", [])
        if results:
            print(f"✅ Found results for '{query}':\n")
            break

for result in results[:10]:
    print(f"ID: {result['id']}")
    print(f"Name: {result['name']}")
    print(f"Films: {len(result.get('parts', []))} films")
    print()

if results:
    best = results[0]
    print(f"👉 Use this in fetch_criterion.py: CRITERION_COLLECTION_ID = {best['id']}")
