"""
imdb_import.py
─────────────────────────────────────────────────────────────────────────────
Imports your IMDb ratings export into tonypedia.csv.

Maps:
  Const         → imdb_id
  Your Rating   → score  (IMDb is 1–10, same scale as Tonypedia)
  Title         → title
  Year          → year
  IMDb Rating   → tmdb_score (community reference)

Rules:
  - Only imports movies (Title Type == "Movie")
  - Smart merge: existing tonypedia.csv entries are NEVER overwritten
  - notes column is left blank for you to fill in
  - Skips duplicates already in tonypedia.csv

USAGE:
  python imdb_import.py

Place your IMDb export CSV in the same folder as this script,
or update IMDB_FILE below to point to it.
─────────────────────────────────────────────────────────────────────────────
"""

import csv
import os
import glob

TONYPEDIA_FILE = "tonypedia.csv"
FIELDNAMES     = ["imdb_id", "score", "notes", "title", "year", "tmdb_score"]

# Auto-detect the IMDb export file — looks for any CSV with 'rating' in the name,
# or falls back to the most recently modified CSV in the folder
def find_imdb_file():
    # Common IMDb export filenames
    candidates = (
        glob.glob("ratings.csv") +
        glob.glob("imdb_ratings*.csv") +
        glob.glob("IMDB_ratings*.csv") +
        glob.glob("*.csv")
    )
    # Exclude tonypedia.csv itself
    candidates = [f for f in candidates if "tonypedia" not in f.lower()]
    if not candidates:
        return None
    # Return most recently modified
    return max(candidates, key=os.path.getmtime)


def load_tonypedia() -> dict:
    """Load existing tonypedia.csv keyed by imdb_id."""
    if not os.path.exists(TONYPEDIA_FILE):
        return {}
    with open(TONYPEDIA_FILE, newline="", encoding="utf-8") as f:
        return {row["imdb_id"]: row for row in csv.DictReader(f)}


def save_tonypedia(entries: dict):
    with open(TONYPEDIA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(entries.values())


def main():
    # ── Find IMDb export ──────────────────────────────────────────────────────
    imdb_file = find_imdb_file()
    if not imdb_file:
        print("❌ No IMDb export CSV found in this folder.")
        print("   Download it from: imdb.com/user/YOUR_ID/ratings → ⋮ → Export")
        return

    print(f"📂 Found IMDb export: {imdb_file}")

    # ── Load existing tonypedia.csv ───────────────────────────────────────────
    existing = load_tonypedia()
    print(f"📂 Existing tonypedia.csv: {len(existing)} entries")

    # ── Parse IMDb export ─────────────────────────────────────────────────────
    added      = 0
    skipped    = 0
    non_movie  = 0

    with open(imdb_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:

            # Only import movies, skip TV shows / episodes
            if row.get("Title Type", "").strip().lower() != "movie":
                non_movie += 1
                continue

            imdb_id = row.get("Const", "").strip()
            if not imdb_id:
                continue

            # Skip if already in tonypedia.csv
            if imdb_id in existing:
                skipped += 1
                continue

            # Map IMDb score (1–10) directly to Tonypedia score
            your_rating = row.get("Your Rating", "").strip()
            imdb_score  = row.get("IMDb Rating", "").strip()
            title       = row.get("Title", "").strip()
            year        = str(row.get("Year", "")).strip()

            existing[imdb_id] = {
                "imdb_id":    imdb_id,
                "score":      your_rating,   # Your personal IMDb rating → Tonypedia score
                "notes":      "",             # Fill in manually
                "title":      title,
                "year":       year,
                "tmdb_score": imdb_score,     # Community IMDb score as reference
            }
            added += 1

    # ── Save ──────────────────────────────────────────────────────────────────
    save_tonypedia(existing)

    print(f"\n✅ Import complete!")
    print(f"   Added    : {added} new films")
    print(f"   Skipped  : {skipped} already in tonypedia.csv (preserved)")
    print(f"   Non-movie: {non_movie} TV/other entries ignored")
    print(f"   Total    : {len(existing)} entries in tonypedia.csv")
    print(f"\n📝 Next steps:")
    print(f"   1. Open tonypedia.csv in Excel")
    print(f"   2. Review/adjust 'score' column — currently mirrors your IMDb ratings")
    print(f"   3. Fill in 'notes' for films you want editorial coverage on")
    print(f"   4. Upload via POST /admin/ratings/upload once backend is live")


if __name__ == "__main__":
    main()
