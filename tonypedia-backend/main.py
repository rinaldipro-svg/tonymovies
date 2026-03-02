import os
import pickle
import json
import numpy as np
import requests
import anthropic
from difflib import SequenceMatcher

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import csv
import io

# --- DATABASE INIT ---
models.Base.metadata.create_all(bind=engine)

# --- ANTHROPIC CLIENT ---
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- VOYAGE AI CLIENT (embeddings) ---
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"

# --- LOAD PRE-COMPUTED EMBEDDINGS (generated once, reused on every request) ---
with open("movie_embeddings.pkl", "rb") as f:
    MOVIE_EMBEDDINGS = pickle.load(f)  # dict: {movie_id: np.array}

with open("movie_data.pkl", "rb") as f:
    MOVIE_DATA = pickle.load(f)  # dict: {movie_id: {title, plot, imdb_id, ...}}

# --- LOAD CRITERION COLLECTION FILMS ---
CRITERION_FILMS = set()
if os.path.exists("criterion_films.json"):
    try:
        with open("criterion_films.json", "r", encoding="utf-8") as f:
            criterion_data = json.load(f)
            CRITERION_FILMS = set(criterion_data.keys())
        print(f"✅ Loaded {len(CRITERION_FILMS)} Criterion Collection films")
    except Exception as e:
        print(f"⚠️  Could not load Criterion films: {e}")
        CRITERION_FILMS = set()
else:
    print("⚠️  criterion_films.json not found.")

# --- LOAD OSCAR FILMS ---
OSCAR_FILMS = {}  # Winners: {imdb_id: {categories, award_count}}
OSCAR_NOMINATED = set()  # All nominated

try:
    with open("oscar_films.json", "r", encoding="utf-8") as f:
        oscar_data = json.load(f)
        OSCAR_FILMS = oscar_data
    
    with open("oscar_nominated.json", "r", encoding="utf-8") as f:
        oscar_nominated_list = json.load(f)
        OSCAR_NOMINATED = set(oscar_nominated_list)
    
    print(f"✅ Loaded {len(OSCAR_FILMS)} Oscar-winning films")
    print(f"✅ Loaded {len(OSCAR_NOMINATED)} Oscar-nominated films")
except Exception as e:
    print(f"⚠️  Could not load Oscar data: {e}")
    OSCAR_FILMS = {}
    OSCAR_NOMINATED = set()

# --- LOAD PALME D'OR FILMS ---
PALME_DOR_WINNERS = set()

try:
    with open("palme_dor_winners.json", "r", encoding="utf-8") as f:
        palme_data = json.load(f)
        PALME_DOR_WINNERS = set(palme_data.keys())
    
    print(f"✅ Loaded {len(PALME_DOR_WINNERS)} Palme d'Or-winning films")
except Exception as e:
    print(f"⚠️  Could not load Palme d'Or data: {e}")
    PALME_DOR_WINNERS = set()

# --- AWARD STATISTICS ---
print(f"\n🏆 AWARDS SUMMARY:")
print(f"  Oscar Winners: {len(OSCAR_FILMS)}")
print(f"  Oscar Nominated: {len(OSCAR_NOMINATED)}")
print(f"  Palme d'Or Winners: {len(PALME_DOR_WINNERS)}")
print(f"  Criterion Collection: {len(CRITERION_FILMS)}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# DUAL-LAYER CRITERIA MAPS
# ═══════════════════════════════════════════════════════════════════════════════
# Keys: User-facing labels (UI)
# Values: Embedding text (rich, evocative, semantically dense for Voyage AI)

MOOD_MAP = {
    "Thrilling":                "heart-pounding suspense, edge-of-seat tension, adrenaline and survival instinct",
    "Heartwarming":             "emotional comfort, uplifting human connection, feel-good catharsis and hope",
    "Melancholic":              "slow immersive sorrow, bittersweet nostalgia, atmospheric quiet beauty and longing",
    "Mind-bending":             "cerebral labyrinthine puzzle, psychological complexity, reality-questioning twists",
    "Darkly comic":             "pitch-black humor, absurdist satire, uncomfortable laughter at human folly",
    "Romantic":                 "passionate intimacy, tender love, magnetic chemistry and emotional vulnerability",
    "Haunting":                 "lingering atmospheric dread, eerie unease, images that haunt long after viewing",
    "Euphoric":                 "explosive joy, celebration of life, high-energy exuberance and infectious delight",
    "Tense":                    "paranoid claustrophobic pressure, slow-burn anxiety, trust is scarce and stakes are lethal",
    "Contemplative":            "stoic philosophical reflection, meditative stillness, quiet resilience and inner depth",
    "Triumphant":               "hard-fought victory against impossible odds, unyielding determination and cathartic payoff",
    "Visceral":                 "raw unfiltered intensity, kinetic explosive momentum, primal physical experience",
}

TOPIC_MAP = {
    "Identity & self-discovery":    "searching for identity, understanding the self, transformation and personal awakening",
    "Family & relationships":       "family bonds and fractures, generational conflict, the weight of love and obligation",
    "Power & corruption":           "geopolitical chess and statecraft, the mechanics of power, corruption at the highest levels",
    "Survival & resilience":        "existential resilience, surviving extreme conditions, enduring isolation and impossible odds",
    "Love & heartbreak":            "the arc of love from passion to loss, romantic devotion, the agony of heartbreak",
    "Justice & morality":           "absolute justice and retribution, moral ambiguity, the line between right and vengeance",
    "War & conflict":               "the brutality and humanity of war, soldiers and civilians, the cost of conflict",
    "Art & creativity":             "the obsessive pursuit of artistic creation, genius and madness, the price of making art",
    "Isolation & loneliness":       "profound solitude, disconnection from humanity, the echo chamber of being alone",
    "Freedom & rebellion":          "defiance against oppression, the fight for liberty, rebellion as an act of self-definition",
    "Coming of age":                "the turbulence of growing up, first experiences, innocence colliding with the real world",
    "Obsession & ambition":         "all-consuming obsession, ruthless ambition, the cost of wanting something too much",
    "The heist & the con":          "clockwork precision, assembling the team, executing the impossible plan with style",
    "History & civilization":       "the rise and fall of empires, historical ascendance and ruin, defining eras of humanity",
    "Science & the unknown":        "cosmic scale and theoretical realities, deep space, the edge of human knowledge",
}

VIBE_MAP = {
    "Cinematic & epic":         "sweeping colossal scale, grand orchestral score, IMAX-level visual immersion and grandeur",
    "Raw & gritty":             "gritty cinema verité, handheld camera, natural lighting, unflinching street-level realism",
    "Dreamlike & surreal":      "transcendent audiovisual odyssey, experimental pacing, dreamlike sequences and poetic imagery",
    "Intimate & quiet":         "delicate small-scale character study, hushed conversations, emotional restraint and nuance",
    "Stylish & cool":           "neon-drenched nocturnal style, auteur precision, sharp dialogue and meticulous visual framing",
    "Nostalgic & warm":         "golden-hour warmth, retro analog texture, memory and sentimentality drenched in amber light",
    "Bleak & unflinching":      "harsh confrontational bleakness, no comfort offered, stark and pitiless observation of reality",
    "Whimsical & playful":      "quirky inventive charm, lighthearted visual wit, imaginative and joyfully unconventional",
}

GENRES = [
    "Drama",
    "Comedy",
    "Thriller",
    "Horror",
    "Sci-Fi",
    "Romance",
    "Action",
    "Documentary",
    "Animation",
    "Crime",
    "War",
    "Fantasy",
    "Musical",
    "Western",
]

ERA_MAP = {
    "Pre-1960 (Golden Age)":                "classic golden age Hollywood cinema, black and white, foundational filmmaking",
    "1960-1979 (New Wave)":                 "new wave revolution, countercultural cinema, auteur-driven experimentation",
    "1980-1999 (Modern Classics)":          "analog era blockbusters, the indie renaissance, iconic 80s and 90s cinema",
    "2000-2014 (Digital Age)":              "digital frontier filmmaking, post-9/11 cinema, early streaming era",
    "2015-Present (Contemporary)":          "modern auteur cinema, post-cinema era, contemporary prestige filmmaking",
}

ERA_YEAR_RANGES = {
    "Pre-1960 (Golden Age)":        (0, 1959),
    "1960-1979 (New Wave)":         (1960, 1979),
    "1980-1999 (Modern Classics)":  (1980, 1999),
    "2000-2014 (Digital Age)":      (2000, 2014),
    "2015-Present (Contemporary)":  (2015, 2099),
}


app = FastAPI(title="Tonypedia AI Backend", version="3.0.0")

# --- CORS (allows Expo mobile app to communicate) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB SESSION DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def build_embedding_query(mood: str, topic: str, vibe: str, genre: str = None, era: str = None) -> str:
    """
    Convert user-facing labels into a semantically rich embedding query.
    
    The dual-layer mapping (label -> embedding_text) is the engine's secret weapon.
    Users see simple labels. Voyage AI sees rich, evocative descriptions.
    
    CRITICAL: Do NOT inject award language here. The embedding represents what
    the user wants to FEEL, not what awards they want. Award-aware text pollutes
    the semantic vector space and degrades search quality.
    """
    mood_emb = MOOD_MAP.get(mood, mood)      # fallback to raw label if not found
    topic_emb = TOPIC_MAP.get(topic, topic)
    vibe_emb = VIBE_MAP.get(vibe, vibe)
    
    query = (
        f"A film that feels {mood_emb}. "
        f"It explores themes of {topic_emb}. "
        f"The sensory experience is {vibe_emb}."
    )
    
    if genre:
        query += f" The genre is {genre}."
    if era:
        era_emb = ERA_MAP.get(era, era)
        query += f" From the era of {era_emb}."
    
    return query


def embed_text(text: str) -> np.ndarray:
    """Call Voyage AI to embed a text query."""
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"input": [text], "model": "voyage-large-2"}
    r = requests.post(VOYAGE_URL, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return np.array(r.json()["data"][0]["embedding"])


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def filter_by_genre(candidates: list[dict], genre: str = None) -> list[dict]:
    """Filter candidates by genre if specified. Soft filter: falls back to unfiltered if no matches."""
    if not genre:
        return candidates
    
    filtered = []
    for film in candidates:
        film_genre = film.get("genre", "").lower()
        if genre.lower() in film_genre or genre.lower() == "any":
            filtered.append(film)
    
    return filtered if filtered else candidates  # Soft filter: return all if no matches


def filter_by_era(candidates: list[dict], era: str = None) -> list[dict]:
    """
    Filter candidates by era using year ranges.
    
    The era parameter should be a label from ERA_MAP (e.g., "1980-1999 (Modern Classics)")
    Soft filter: falls back to unfiltered if no matches.
    """
    if not era:
        return candidates
    
    year_range = ERA_YEAR_RANGES.get(era)
    if not year_range:
        return candidates  # Unknown era, return all
    
    start_year, end_year = year_range
    filtered = []
    
    for film in candidates:
        year_str = film.get("year", "")
        if not year_str:
            filtered.append(film)  # No year info, include it
            continue
        
        try:
            year = int(year_str)
            if start_year <= year <= end_year:
                filtered.append(film)
        except (ValueError, TypeError):
            filtered.append(film)  # Parse error, include it
    
    return filtered if filtered else candidates  # Soft filter: return all if no matches


def fetch_ratings(imdb_id: str, db: Session) -> dict:
    """Fetch ratings for a film from all sources."""
    if not imdb_id:
        return {"global_average": None, "imdb": None, "rt": None, "metacritic": None, "tmdb": None}
    
    rating = db.query(models.RatingsCache).filter_by(imdb_id=imdb_id).first()
    
    if rating:
        scores = [rating.imdb_score, rating.rt_score, rating.metacritic_score, rating.tmdb_score]
        scores_present = [s for s in scores if s is not None]
        global_avg = sum(scores_present) / len(scores_present) if scores_present else None
        
        return {
            "global_average": global_avg,
            "imdb": rating.imdb_score,
            "rt": rating.rt_score,
            "metacritic": rating.metacritic_score,
            "tmdb": rating.tmdb_score,
        }
    else:
        return {"global_average": None, "imdb": None, "rt": None, "metacritic": None, "tmdb": None}


def batch_fetch_ratings(imdb_ids: list[str], db: Session) -> dict:
    """
    OPTIMIZED: Batch fetch ratings for multiple films.
    Returns dict: {imdb_id: ratings_dict}
    Reduces database queries from N to 1.
    """
    if not imdb_ids:
        return {}
    
    # Single query to fetch all ratings at once
    ratings_records = db.query(models.RatingsCache).filter(
        models.RatingsCache.imdb_id.in_(imdb_ids)
    ).all()
    
    ratings_map = {}
    for record in ratings_records:
        scores = [record.imdb_score, record.rt_score, record.metacritic_score, record.tmdb_score]
        scores_present = [s for s in scores if s is not None]
        global_avg = sum(scores_present) / len(scores_present) if scores_present else None
        
        ratings_map[record.imdb_id] = {
            "global_average": global_avg,
            "imdb": record.imdb_score,
            "rt": record.rt_score,
            "metacritic": record.metacritic_score,
            "tmdb": record.tmdb_score,
        }
    
    # Return default for any missing IDs
    for imdb_id in imdb_ids:
        if imdb_id not in ratings_map:
            ratings_map[imdb_id] = {"global_average": None, "imdb": None, "rt": None, "metacritic": None, "tmdb": None}
    
    return ratings_map


def fetch_poster(imdb_id: str) -> str:
    """Fetch poster URL from TMDB (primary) with OMDb as fallback."""
    tmdb_key = os.getenv("TMDB_API_KEY")
    if tmdb_key and imdb_id:
        try:
            r = requests.get(
                f"https://api.themoviedb.org/3/find/{imdb_id}",
                params={"api_key": tmdb_key, "external_source": "imdb_id"},
                timeout=5
            )
            r.raise_for_status()
            results = r.json().get("movie_results", [])
            if results and results[0].get("poster_path"):
                return f"https://image.tmdb.org/t/p/w400{results[0]['poster_path']}"
        except:
            pass
    
    return None


def fuzzy_match_title(target: str, candidates: list[str], threshold: float = 0.6) -> str:
    """
    Find best matching title using substring and fuzzy matching.
    Returns the best match or None if no good match found.
    """
    target_lower = target.lower().strip()
    
    # First try exact match
    for candidate in candidates:
        if candidate.lower().strip() == target_lower:
            return candidate
    
    # Then try substring match
    for candidate in candidates:
        if target_lower in candidate.lower() or candidate.lower() in target_lower:
            return candidate
    
    # Finally try fuzzy matching
    best_match = None
    best_ratio = threshold
    for candidate in candidates:
        ratio = SequenceMatcher(None, target_lower, candidate.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
    
    return best_match



# ──────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "✅ Tonypedia API v2.1.0 is running",
        "timestamp": "2024",
        "awards_loaded": {
            "oscar_winners": len(OSCAR_FILMS),
            "oscar_nominated": len(OSCAR_NOMINATED),
            "palme_dor_winners": len(PALME_DOR_WINNERS),
            "criterion_films": len(CRITERION_FILMS),
        }
    }


@app.get("/favicon.ico")
def favicon():
    """Prevent favicon 404 errors from cluttering logs."""
    return Response(status_code=204)


@app.get("/recommend")
def recommend(mood: str, topic: str = "Discovery", vibe: str = "Contemplative", 
              genre: str = None, era: str = None, db: Session = Depends(get_db)):
    """
    Main recommendation engine — 3-phase pipeline:
    
    PHASE 1: CANDIDATE POOL ASSEMBLY
      - Build clean embedding query using dual-layer criteria maps
      - Vector search top 40 films by cosine similarity
      - Apply soft genre/era filters
      - Inject Tonypedia films (top 8 most relevant)
      - Inject award films (top 8 most relevant)
      - Deduplicate by imdb_id → pool of ~40-55 films
    
    PHASE 2: CLAUDE RE-RANKING
      - Claude sees full pool with all metadata and tags
      - Claude ranks by mood/criteria match (PRIMARY)
      - Claude respects hard rules (3 Tonypedia min, 3 award min)
      - Claude returns top 10
    
    PHASE 3: ENFORCEMENT & ENRICHMENT
      - Verify hard rule minimums
      - Surgically replace low-ranked films if needed
      - Enrich with full metadata
      - Return exactly 10 results
    """
    
    print(f"\n▶️  RECOMMEND REQUEST: mood={mood} | topic={topic} | vibe={vibe} | genre={genre} | era={era}")
    
    try:
        # ════════════════════════════════════════════════════════════════════════
        # PHASE 1: CANDIDATE POOL ASSEMBLY
        # ════════════════════════════════════════════════════════════════════════
        
        print(f"\n🔍 PHASE 1: Building candidate pool...")
        
        # Step 1: Build clean embedding query (no award context)
        query_text = build_embedding_query(mood, topic, vibe, genre, era)
        print(f"   Embedding query: {query_text[:80]}...")
        
        # Step 2: Embed using Voyage AI
        mood_vector = embed_text(query_text)
        print(f"   ✅ Query embedded")
        
        # Step 3: Vector search top 40 (not 15 — we need a big pool)
        similarities_array = np.array([
            cosine_similarity(mood_vector, embedding)
            for embedding in MOVIE_EMBEDDINGS.values()
        ])
        movie_ids = list(MOVIE_EMBEDDINGS.keys())
        
        # Use argpartition for O(n) top-k selection
        target_k = min(40, len(similarities_array))
        if len(similarities_array) > target_k:
            top_indices = np.argpartition(similarities_array, -target_k)[-target_k:]
            top_indices = top_indices[np.argsort(-similarities_array[top_indices])]  # Sort descending
        else:
            top_indices = np.argsort(-similarities_array)
        
        # Build initial candidate pool from top 40
        vector_pool = []
        for idx in top_indices:
            movie_id = movie_ids[idx]
            film = MOVIE_DATA.get(movie_id, {}).copy()
            if film.get("imdb_id"):
                film["similarity"] = float(similarities_array[idx])
                vector_pool.append(film)
        
        print(f"   ✅ Vector search: {len(vector_pool)} films from top 40")
        
        # Step 4: Apply soft filters (genre, era)
        filtered_pool = filter_by_genre(vector_pool, genre)
        print(f"   ✅ Genre filter: {len(filtered_pool)} films")
        
        filtered_pool = filter_by_era(filtered_pool, era)
        print(f"   ✅ Era filter: {len(filtered_pool)} films")
        
        # If soft filter reduced pool too much, fall back to unfiltered
        if len(filtered_pool) < 30:
            print(f"   ⚠️  Pool too small after soft filters ({len(filtered_pool)} < 30), falling back")
            filtered_pool = vector_pool
        
        # Step 5: Inject guaranteed Tonypedia films
        tonypedia_films = db.query(models.TonypediaRating).all()
        existing_ids = {f.get("imdb_id") for f in filtered_pool}
        
        tonypedia_candidates = []
        for tp_entry in tonypedia_films:
            if tp_entry.imdb_id in existing_ids:
                continue  # Already in pool
            film = next((f for f in MOVIE_DATA.values() if f.get("imdb_id") == tp_entry.imdb_id), None)
            if film:
                film_copy = film.copy()
                # Compute similarity for ranking
                if film_copy.get("imdb_id") in MOVIE_EMBEDDINGS:
                    emb = MOVIE_EMBEDDINGS[film_copy["imdb_id"]]
                    film_copy["similarity"] = cosine_similarity(mood_vector, emb)
                else:
                    film_copy["similarity"] = 0.0
                film_copy["tonypedia_score"] = tp_entry.score
                tonypedia_candidates.append(film_copy)
        
        # Sort by similarity and take top 8
        tonypedia_candidates.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        injected_tonypedia = tonypedia_candidates[:8]
        filtered_pool.extend(injected_tonypedia)
        print(f"   ✅ Injected {len(injected_tonypedia)} Tonypedia films")
        
        # Step 6: Inject guaranteed award films
        award_candidates = []
        award_pool_ids = {f.get("imdb_id") for f in filtered_pool}
        
        for movie_id, film_data in MOVIE_DATA.items():
            imdb_id = film_data.get("imdb_id")
            if not imdb_id or imdb_id in award_pool_ids:
                continue
            
            # Check if it's an award film
            if imdb_id in OSCAR_FILMS or imdb_id in PALME_DOR_WINNERS or imdb_id in CRITERION_FILMS:
                film_copy = film_data.copy()
                # Compute similarity
                if movie_id in MOVIE_EMBEDDINGS:
                    emb = MOVIE_EMBEDDINGS[movie_id]
                    film_copy["similarity"] = cosine_similarity(mood_vector, emb)
                else:
                    film_copy["similarity"] = 0.0
                award_candidates.append(film_copy)
        
        # Sort by similarity and take top 8
        award_candidates.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        injected_awards = award_candidates[:8]
        filtered_pool.extend(injected_awards)
        print(f"   ✅ Injected {len(injected_awards)} award films")
        
        # Step 7: Deduplicate by imdb_id
        seen_ids = set()
        dedup_pool = []
        for film in filtered_pool:
            imdb_id = film.get("imdb_id")
            if imdb_id and imdb_id not in seen_ids:
                dedup_pool.append(film)
                seen_ids.add(imdb_id)
        
        print(f"   ✅ Deduped: {len(dedup_pool)} unique films in candidate pool")
        
        if len(dedup_pool) == 0:
            print(f"   ❌ Empty candidate pool!")
            return {"results": [], "session_id": None, "error": "No films found matching criteria"}
        
        # ════════════════════════════════════════════════════════════════════════
        # PHASE 2: CLAUDE RE-RANKING
        # ════════════════════════════════════════════════════════════════════════
        
        print(f"\n🤖 PHASE 2: Claude re-ranking...")
        
        # Batch fetch all ratings for the pool
        pool_imdb_ids = [f.get("imdb_id") for f in dedup_pool if f.get("imdb_id")]
        batch_ratings = batch_fetch_ratings(pool_imdb_ids, db)
        
        # Build candidate block with tags
        candidate_lines = []
        for idx, film in enumerate(dedup_pool, 1):
            imdb_id = film.get("imdb_id", "")
            title = film.get("title", "Unknown")
            year = film.get("year", "")
            genre_str = film.get("genre", "")
            
            # Compute global average for this pool item
            ratings = batch_ratings.get(imdb_id, {})
            global_avg = ratings.get("global_average")
            
            # Build tag list
            tags = []
            
            # Check Tonypedia
            tp_entry = db.query(models.TonypediaRating).filter_by(imdb_id=imdb_id).first()
            if tp_entry and tp_entry.score:
                tags.append(f"TONYPEDIA({tp_entry.score})")
            
            # Check awards
            if imdb_id in OSCAR_FILMS:
                tags.append("OSCAR")
            if imdb_id in PALME_DOR_WINNERS:
                tags.append("PALME D'OR")
            if imdb_id in CRITERION_FILMS:
                tags.append("CRITERION")
            
            # Format line
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            avg_str = f" — Avg: {global_avg:.1f}/10" if global_avg else ""
            
            candidate_lines.append(f"{idx}. {title} ({year}) {genre_str}{tag_str}{avg_str}")
        
        candidate_block = "\n".join(candidate_lines)
        
        # Build Claude prompt with hard rules clearly stated
        claude_prompt = f"""You are Tonypedia's expert film curator. Your job: select and rank exactly 10 films from the candidate pool below that best match the user's search criteria.

USER CRITERIA:
- Mood: {mood}
- Topic: {topic}
- Vibe: {vibe}
{f"- Genre: {genre}" if genre else ""}
{f"- Era: {era}" if era else ""}

HARD RULES (you MUST follow these):
1. Return EXACTLY 10 films.
2. At least 3 films must be marked [TONYPEDIA]. If fewer than 3 Tonypedia films match the mood well, still include 3 — pick the closest matches.
3. At least 3 films must be marked with at least one of [OSCAR], [PALME D'OR], or [CRITERION]. A single film can satisfy this if it has multiple tags. If fewer than 3 award films match well, still include 3 — pick the closest matches.
4. A film can count toward BOTH the Tonypedia minimum AND the award minimum if it has both tags.

SOFT RULES (follow when choosing between otherwise equal candidates):
- Prefer [TONYPEDIA] films — they are personally curated and carry the highest trust.
- Prefer [OSCAR] films — they represent industry-recognized excellence.
- Prefer [PALME D'OR] films — they represent international artistic excellence.
- Prefer [CRITERION] films — they represent enduring cinematic significance.
- Prefer films with higher global ratings when mood relevance is equal.

RANKING PRIORITY: Mood/criteria match is KING. A perfectly matching untagged film should rank above a poorly matching tagged film. Tags are tiebreakers, not overrides.

CANDIDATE POOL:
{candidate_block}

Respond with ONLY a JSON array, no markdown, no explanation:
[
  {{"rank": 1, "title": "Exact Film Title", "reason": "One sentence, max 20 words, explaining the mood match"}},
  {{"rank": 2, "title": "Another Title", "reason": "Why this matches"}},
  ...10 entries total...
]"""
        
        # Call Claude
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": claude_prompt}]
        )
        
        if not message.content or len(message.content) == 0:
            raise ValueError("Claude returned empty content")
        
        raw_response = message.content[0].text.strip()
        print(f"   ✅ Claude responded")
        
        # Strip markdown fences if present
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        if raw_response.startswith("```"):
            raw_response = raw_response[3:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]
        raw_response = raw_response.strip()
        
        # Parse JSON
        try:
            claude_ranking = json.loads(raw_response)
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Claude JSON parse failed: {e}")
            print(f"   Retrying with stricter prompt...")
            
            # Retry with stricter prompt
            retry_prompt = claude_prompt.replace(
                "Respond with ONLY a JSON array",
                "You MUST respond with ONLY valid JSON array. No other text. Start with [ and end with ]."
            )
            message = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": retry_prompt}]
            )
            
            raw_response = message.content[0].text.strip()
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:]
            if raw_response.startswith("```"):
                raw_response = raw_response[3:]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3]
            raw_response = raw_response.strip()
            
            try:
                claude_ranking = json.loads(raw_response)
            except json.JSONDecodeError as e2:
                print(f"   ❌ Retry also failed: {e2}")
                print(f"   Fallback to similarity-based ranking")
                
                # Fallback: rank by similarity score
                dedup_pool.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                claude_ranking = [
                    {"rank": i+1, "title": f["title"], "reason": "Fallback ranking"}
                    for i, f in enumerate(dedup_pool[:10])
                ]
        
        print(f"   ✅ Claude ranked {len(claude_ranking)} films")
        
        # ════════════════════════════════════════════════════════════════════════
        # PHASE 3: ENFORCEMENT & ENRICHMENT
        # ════════════════════════════════════════════════════════════════════════
        
        print(f"\n📋 PHASE 3: Enforcement & enrichment...")
        
        # Step 1: Map Claude's titles back to film objects
        pool_titles = {f.get("title", ""): f for f in dedup_pool}
        top_10_films = []
        remaining_pool = list(dedup_pool)
        
        for rank_obj in claude_ranking[:10]:
            claude_title = rank_obj.get("title", "")
            
            # Try exact match, then fuzzy match
            film = pool_titles.get(claude_title)
            if not film:
                # Try fuzzy matching
                matching_title = fuzzy_match_title(claude_title, list(pool_titles.keys()), threshold=0.6)
                if matching_title:
                    film = pool_titles[matching_title]
            
            if film:
                film["claude_reason"] = rank_obj.get("reason", "")
                film["claude_rank"] = len(top_10_films) + 1
                top_10_films.append(film)
                if film in remaining_pool:
                    remaining_pool.remove(film)
        
        print(f"   ✅ Mapped {len(top_10_films)} Claude films back to pool")
        
        # Step 2: Enforce hard rules — count current tags
        tonypedia_films_in_top10 = [f for f in top_10_films if db.query(models.TonypediaRating).filter_by(imdb_id=f.get("imdb_id")).first()]
        award_films_in_top10 = [f for f in top_10_films if f.get("imdb_id") in OSCAR_FILMS or f.get("imdb_id") in PALME_DOR_WINNERS or f.get("imdb_id") in CRITERION_FILMS]
        
        print(f"   Current: {len(tonypedia_films_in_top10)} Tonypedia, {len(award_films_in_top10)} award films")
        
        # Step 2a: Enforce Tonypedia minimum (3)
        if len(tonypedia_films_in_top10) < 3:
            needed = 3 - len(tonypedia_films_in_top10)
            # Find remaining Tonypedia films sorted by similarity
            remaining_tp = [f for f in remaining_pool if db.query(models.TonypediaRating).filter_by(imdb_id=f.get("imdb_id")).first()]
            remaining_tp.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            for i, tp_film in enumerate(remaining_tp[:needed]):
                # Replace lowest-ranked non-essential film
                for j in range(len(top_10_films) - 1, -1, -1):
                    candidate_for_replacement = top_10_films[j]
                    # Don't replace if it's the only representative of another rule
                    is_sole_award = (candidate_for_replacement in award_films_in_top10 and len(award_films_in_top10) == 3)
                    if not is_sole_award:
                        top_10_films.pop(j)
                        remaining_pool.remove(tp_film)
                        top_10_films.append(tp_film)
                        tonypedia_films_in_top10.append(tp_film)
                        if tp_film in remaining_pool:
                            remaining_pool.remove(tp_film)
                        break
        
        # Step 2b: Enforce award minimum (3)
        if len(award_films_in_top10) < 3:
            needed = 3 - len(award_films_in_top10)
            # Find remaining award films sorted by similarity
            remaining_awards = [f for f in remaining_pool if f.get("imdb_id") in OSCAR_FILMS or f.get("imdb_id") in PALME_DOR_WINNERS or f.get("imdb_id") in CRITERION_FILMS]
            remaining_awards.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            for i, award_film in enumerate(remaining_awards[:needed]):
                # Replace lowest-ranked non-essential film
                for j in range(len(top_10_films) - 1, -1, -1):
                    candidate_for_replacement = top_10_films[j]
                    # Don't replace if it's the only representative of Tonypedia rule
                    is_sole_tonypedia = (candidate_for_replacement in tonypedia_films_in_top10 and len(tonypedia_films_in_top10) == 3)
                    if not is_sole_tonypedia:
                        top_10_films.pop(j)
                        if award_film in remaining_pool:
                            remaining_pool.remove(award_film)
                        top_10_films.append(award_film)
                        award_films_in_top10.append(award_film)
                        break
        
        # Trim to exactly 10
        final_top_10 = top_10_films[:10]
        
        print(f"   ✅ Hard rules enforced: {len([f for f in final_top_10 if db.query(models.TonypediaRating).filter_by(imdb_id=f.get('imdb_id')).first()])} Tonypedia, {len([f for f in final_top_10 if f.get('imdb_id') in OSCAR_FILMS or f.get('imdb_id') in PALME_DOR_WINNERS or f.get('imdb_id') in CRITERION_FILMS])} award")
        
        # Step 3: Enrich with full metadata
        tp_map = {}
        if pool_imdb_ids:
            tp_entries = db.query(models.TonypediaRating).filter(
                models.TonypediaRating.imdb_id.in_(pool_imdb_ids)
            ).all()
            tp_map = {entry.imdb_id: entry for entry in tp_entries}
        
        enriched_results = []
        for idx, film in enumerate(final_top_10):
            imdb_id = film.get("imdb_id", "")
            ratings = batch_ratings.get(imdb_id, {"global_average": None, "imdb": None, "rt": None, "metacritic": None, "tmdb": None})
            poster = film.get("poster") or fetch_poster(imdb_id)
            
            tp_entry = tp_map.get(imdb_id)
            is_tonypedia = bool(tp_entry and tp_entry.score)
            tonypedia_score = tp_entry.score if tp_entry else None
            tonypedia_notes = tp_entry.notes if (tp_entry and tp_entry.notes) else None
            
            is_criterion = imdb_id in CRITERION_FILMS
            is_oscar_winner = imdb_id in OSCAR_FILMS
            is_oscar_nominated = imdb_id in OSCAR_NOMINATED
            is_palme_dor_winner = imdb_id in PALME_DOR_WINNERS
            
            explanation = film.get("claude_reason", "")
            if is_tonypedia and tonypedia_notes:
                explanation = tonypedia_notes
            
            enriched_results.append({
                "rank": idx + 1,
                "title": film.get("title", "Unknown"),
                "year": film.get("year", ""),
                "plot": film.get("plot", ""),
                "poster": poster,
                "explanation": explanation,
                "global_average": ratings["global_average"],
                "tonypedia_score": tonypedia_score,
                "is_tonypedia": is_tonypedia,
                "is_criterion": is_criterion,
                "is_oscar_winner": is_oscar_winner,
                "is_oscar_nominated": is_oscar_nominated,
                "is_palme_dor_winner": is_palme_dor_winner,
                "imdb_id": imdb_id,
                "scores": {
                    "imdb": ratings["imdb"],
                    "rt": ratings["rt"],
                    "metacritic": ratings["metacritic"],
                    "tmdb": ratings["tmdb"],
                }
            })
        
        print(f"   ✅ Enriched {len(enriched_results)} films with full metadata")
        
        # Step 4: Log session to DB
        session_log = models.MoodSession(
            mood_raw={"mood": mood, "topic": topic, "vibe": vibe, "genre": genre, "era": era},
            result_titles=[f["title"] for f in enriched_results]
        )
        db.add(session_log)
        db.commit()
        
        print(f"✅ RECOMMEND COMPLETE: {len(enriched_results)} films returned\n")
        
        return {"results": enriched_results, "session_id": session_log.id}
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"\n❌ CRITICAL ERROR: {error_msg}")
        print(f"TRACE: {error_trace}\n")
        raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")



@app.get("/tonypedia/browse")
def browse_tonypedia(db: Session = Depends(get_db)):
    """Fetch all Tonypedia-rated films with award badges."""
    
    try:
        # Get all Tonypedia ratings
        tonypedia_ratings = db.query(models.TonypediaRating).all()
        
        # Build reverse lookup for movie data
        imdb_to_data = {film.get("imdb_id"): film for film in MOVIE_DATA.values() if film.get("imdb_id")}
        
        # OPTIMIZED: Batch fetch all ratings at once
        imdb_ids = [tp.imdb_id for tp in tonypedia_ratings]
        batch_ratings = batch_fetch_ratings(imdb_ids, db)
        
        enriched = []
        missing_titles = 0
        
        for tp_entry in tonypedia_ratings:
            imdb_id = tp_entry.imdb_id
            movie_data = imdb_to_data.get(imdb_id, {})
            
            title = movie_data.get("title", "").strip()
            year = movie_data.get("year", "").strip()
            plot = movie_data.get("plot", "").strip()
            
            if not title:
                missing_titles += 1
                continue
            
            ratings = batch_ratings.get(imdb_id, {"global_average": None, "imdb": None, "rt": None, "metacritic": None, "tmdb": None})
            poster = movie_data.get("poster") or fetch_poster(imdb_id)
            
            # Check if Criterion
            is_criterion = imdb_id in CRITERION_FILMS
            
            # Check awards
            is_oscar_winner = imdb_id in OSCAR_FILMS
            is_oscar_nominated = imdb_id in OSCAR_NOMINATED
            is_palme_dor_winner = imdb_id in PALME_DOR_WINNERS
            
            enriched.append({
                "rank": len(enriched) + 1,
                "title": title or "Unknown",
                "year": year,
                "plot": plot,
                "poster": poster,
                "imdb_id": imdb_id,
                "tonypedia_score": tp_entry.score,
                "tonypedia_notes": tp_entry.notes,
                "is_criterion": is_criterion,
                "is_oscar_winner": is_oscar_winner,
                "is_oscar_nominated": is_oscar_nominated,
                "is_palme_dor_winner": is_palme_dor_winner,
                "global_average": ratings["global_average"],
                "scores": {
                    "imdb": ratings["imdb"],
                    "rt": ratings["rt"],
                    "metacritic": ratings["metacritic"],
                    "tmdb": ratings["tmdb"],
                }
            })
        
        print(f"✅ Loaded {len(enriched)} Tonypedia films ({missing_titles} missing titles)")
        return {"results": enriched, "total": len(enriched)}
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"--- CRITICAL ERROR: {error_msg} ---")
        print(f"--- TRACE: {error_trace} ---")
        raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")


@app.post("/tonypedia/rate")
def rate_film(imdb_id: str, score: float, notes: str = "", db: Session = Depends(get_db)):
    """Add or update a Tonypedia rating for a film."""
    
    if not 0 <= score <= 10:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 10")
    
    existing = db.query(models.TonypediaRating).filter_by(imdb_id=imdb_id).first()
    
    if existing:
        existing.score = score
        existing.notes = notes
    else:
        new_rating = models.TonypediaRating(imdb_id=imdb_id, score=score, notes=notes)
        db.add(new_rating)
    
    db.commit()
    return {"status": "success", "imdb_id": imdb_id, "score": score}


@app.post("/tonypedia/import")
def import_tonypedia(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import Tonypedia ratings from CSV."""
    
    try:
        contents = file.file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(contents))
        
        count = 0
        for row in reader:
            imdb_id = row.get("imdb_id", "").strip()
            score_str = row.get("score", "").strip()
            notes = row.get("notes", "").strip()
            
            if not imdb_id or not score_str:
                continue
            
            try:
                score = float(score_str)
            except ValueError:
                continue
            
            existing = db.query(models.TonypediaRating).filter_by(imdb_id=imdb_id).first()
            if existing:
                existing.score = score
                existing.notes = notes
            else:
                new_rating = models.TonypediaRating(imdb_id=imdb_id, score=score, notes=notes)
                db.add(new_rating)
            
            count += 1
        
        db.commit()
        return {"status": "success", "imported": count}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
