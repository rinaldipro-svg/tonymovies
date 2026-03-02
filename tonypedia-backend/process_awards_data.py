"""
process_awards_data.py
─────────────────────────────────────────────────────────────────────────────
Process Oscar (CSV) and Palme d'Or (CSV) data into JSON files
for fast in-memory loading in the backend.

Usage:
  python process_awards_data.py
"""

import pandas as pd
import json
from collections import defaultdict

print("🎬 Processing Awards Data...\n")

# ──────────────────────────────────────────────────────────────────────────
# 1. PROCESS OSCAR DATA
# ──────────────────────────────────────────────────────────────────────────

print("📺 Processing Oscar data...")

try:
    oscar_df = pd.read_csv('full_data.csv', sep='\t', encoding='utf-8')
    print(f"   Loaded {len(oscar_df)} Oscar records")
    
    # Extract unique films
    oscar_films = {}
    oscar_nominated = set()
    
    for _, row in oscar_df.iterrows():
        imdb_id = row['FilmId']
        title = row['Film']
        year = row['Year']
        category = row['CanonicalCategory']
        is_winner = row['Winner'] == True
        
        # Skip if no IMDb ID
        if not imdb_id or not str(imdb_id).startswith('tt'):
            continue
        
        # Track nominated
        oscar_nominated.add(imdb_id)
        
        # Track winners with details
        if is_winner:
            if imdb_id not in oscar_films:
                oscar_films[imdb_id] = {
                    'title': str(title),
                    'year': str(year),
                    'is_winner': True,
                    'categories': [],
                    'award_count': 0
                }
            
            if category not in oscar_films[imdb_id]['categories']:
                oscar_films[imdb_id]['categories'].append(category)
            oscar_films[imdb_id]['award_count'] += 1
    
    # Save Oscar data
    with open('oscar_films.json', 'w', encoding='utf-8') as f:
        json.dump(oscar_films, f, indent=2)
    
    with open('oscar_nominated.json', 'w', encoding='utf-8') as f:
        json.dump(list(oscar_nominated), f, indent=2)
    
    print(f"   ✅ Found {len(oscar_films)} Oscar WINNERS")
    print(f"   ✅ Found {len(oscar_nominated)} Oscar NOMINATED films")
    print(f"   ✅ Saved: oscar_films.json, oscar_nominated.json")
    
    # Show sample
    print(f"\n   📋 Oscar Winner Sample:")
    for imdb_id, data in list(oscar_films.items())[:3]:
        print(f"      {imdb_id}: {data['title']} - {data['award_count']} awards")

except Exception as e:
    print(f"   ❌ Error processing Oscar data: {e}")

# ──────────────────────────────────────────────────────────────────────────
# 2. PROCESS PALME D'OR DATA
# ──────────────────────────────────────────────────────────────────────────

print("\n🌹 Processing Palme d'Or data...")

try:
    palme_df = pd.read_csv('palme_dor_winners.csv', encoding='utf-8')
    print(f"   Loaded {len(palme_df)} Palme d'Or records")
    
    # Extract unique films
    palme_dor_films = {}
    
    for _, row in palme_df.iterrows():
        imdb_id = row['imdb_id']
        title = row['title']
        year = row['year']
        award_year = row['award_year']
        
        # Skip if no IMDb ID
        if not imdb_id or not str(imdb_id).startswith('tt'):
            continue
        
        if imdb_id not in palme_dor_films:
            palme_dor_films[imdb_id] = {
                'title': str(title),
                'year': str(year),
                'award_year': str(award_year),
                'is_winner': True
            }
    
    # Save Palme d'Or data
    with open('palme_dor_winners.json', 'w', encoding='utf-8') as f:
        json.dump(palme_dor_films, f, indent=2)
    
    print(f"   ✅ Found {len(palme_dor_films)} Palme d'Or WINNERS")
    print(f"   ✅ Saved: palme_dor_winners.json")
    
    # Show sample
    print(f"\n   📋 Palme d'Or Winner Sample:")
    for imdb_id, data in list(palme_dor_films.items())[:3]:
        print(f"      {imdb_id}: {data['title']} ({data['year']})")

except Exception as e:
    print(f"   ❌ Error processing Palme d'Or data: {e}")

# ──────────────────────────────────────────────────────────────────────────
# 3. SUMMARY
# ──────────────────────────────────────────────────────────────────────────

print("\n" + "="*70)
print("✅ Awards Data Processing Complete!")
print("="*70)

print("\nGenerated Files:")
print("  1. oscar_films.json         - Oscar winners with details")
print("  2. oscar_nominated.json     - All Oscar-nominated film IDs")
print("  3. palme_dor_winners.json   - Palme d'Or winners with details")

print("\nNext Steps:")
print("  1. Copy JSON files to backend directory")
print("  2. Update main.py to load these files at startup")
print("  3. Add award flags to /recommend and /tonypedia/browse endpoints")
print("  4. Test with sample recommendations")

print("\n" + "="*70)
