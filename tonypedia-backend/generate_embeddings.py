import os
import ast
import time
import pickle
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
BATCH_SIZE = 10        # Very small batches for free tier
SLEEP_BETWEEN = 20     # 20 seconds between every batch (3 req/min = 1 per 20s)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load & clean the TMDB dataset
# ──────────────────────────────────────────────────────────────────────────────
print("📂 Loading dataset...")
df = pd.read_csv("tmdb_5000_movies.csv")

def extract_genres(genre_str):
    try:
        genres = ast.literal_eval(genre_str)
        return " ".join([g["name"] for g in genres])
    except:
        return ""

df["clean_genres"] = df["genres"].apply(extract_genres)
df["movie_dna"] = df["overview"].fillna("") + " " + df["clean_genres"]
df = df[df["movie_dna"].str.strip() != ""].reset_index(drop=True)
print(f"✅ {len(df)} movies loaded and cleaned.")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — Resume support: load existing progress if any
# ──────────────────────────────────────────────────────────────────────────────
PROGRESS_FILE = "embeddings_progress.pkl"

if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "rb") as f:
        all_embeddings = pickle.load(f)
    start_index = len(all_embeddings) * BATCH_SIZE
    print(f"▶️  Resuming from batch {len(all_embeddings) * BATCH_SIZE // BATCH_SIZE + 1} ({start_index} movies already done)")
else:
    all_embeddings = []
    start_index = 0
    print("🆕 Starting fresh run.")

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — Embed via Voyage AI with exponential backoff
# ──────────────────────────────────────────────────────────────────────────────
def embed_batch(texts: list[str]) -> list[list[float]]:
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"input": texts, "model": "voyage-large-2"}
    response = requests.post(VOYAGE_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


total_batches = (len(df) - start_index + BATCH_SIZE - 1) // BATCH_SIZE
batch_count = 0

print(f"🚀 Embedding {len(df) - start_index} remaining movies in batches of {BATCH_SIZE}...")
print(f"   Waiting {SLEEP_BETWEEN}s between batches to respect free tier rate limit.")
print(f"   Estimated time: ~{(total_batches * SLEEP_BETWEEN) // 60} minutes\n")

for i in range(start_index, len(df), BATCH_SIZE):
    batch_texts = df["movie_dna"].iloc[i:i + BATCH_SIZE].tolist()
    batch_count += 1
    overall_batch = (i // BATCH_SIZE) + 1

    # Exponential backoff: try up to 5 times
    wait = SLEEP_BETWEEN
    success = False
    for attempt in range(5):
        try:
            embeddings = embed_batch(batch_texts)
            all_embeddings.append(embeddings)
            done = min(i + BATCH_SIZE, len(df))
            print(f"   Batch {overall_batch} ✅ ({done}/{len(df)} movies)")
            success = True
            break
        except Exception as e:
            if "429" in str(e):
                print(f"   Batch {overall_batch} ⏳ Rate limited. Waiting {wait}s (attempt {attempt+1}/5)...")
                time.sleep(wait)
                wait *= 2  # Exponential backoff: 20s → 40s → 80s → 160s
            else:
                print(f"   Batch {overall_batch} ❌ Unexpected error: {e}")
                raise

    if not success:
        print(f"   Batch {overall_batch} 💀 Failed after 5 attempts. Progress saved — re-run to resume.")
        # Save progress before exiting
        with open(PROGRESS_FILE, "wb") as f:
            pickle.dump(all_embeddings, f)
        raise RuntimeError("Too many retries. Run the script again to resume from where it stopped.")

    # Save progress every 10 batches
    if batch_count % 10 == 0:
        with open(PROGRESS_FILE, "wb") as f:
            pickle.dump(all_embeddings, f)
        print(f"   💾 Progress saved ({done}/{len(df)} movies)")

    # Throttle between batches
    if i + BATCH_SIZE < len(df):
        time.sleep(SLEEP_BETWEEN)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — Flatten and save final outputs
# ──────────────────────────────────────────────────────────────────────────────
print("\n💾 Building final movie_embeddings.pkl...")
flat_embeddings = [emb for batch in all_embeddings for emb in batch]

movie_embeddings = {}
for idx, row in df.iterrows():
    if idx < len(flat_embeddings):
        movie_embeddings[str(row["id"])] = flat_embeddings[idx]

with open("movie_embeddings.pkl", "wb") as f:
    pickle.dump(movie_embeddings, f)
print(f"   ✅ Saved {len(movie_embeddings)} embeddings to movie_embeddings.pkl")

print("💾 Building movie_data.pkl...")
movie_data = {}
for _, row in df.iterrows():
    movie_id = str(row["id"])
    movie_data[movie_id] = {
        "title":   row.get("title", "Unknown"),
        "plot":    row.get("overview", ""),
        "year":    str(row.get("release_date", ""))[:4] if pd.notna(row.get("release_date")) else "",
        "imdb_id": row.get("imdb_id", "") if "imdb_id" in df.columns else "",
    }

with open("movie_data.pkl", "wb") as f:
    pickle.dump(movie_data, f)
print(f"   ✅ Saved {len(movie_data)} records to movie_data.pkl")

# Clean up progress file
if os.path.exists(PROGRESS_FILE):
    os.remove(PROGRESS_FILE)

print("\n🎬 All done! Both .pkl files are ready. You can now push to Railway.")
