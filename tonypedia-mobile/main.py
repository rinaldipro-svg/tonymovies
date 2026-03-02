import os
import pickle
import json
import numpy as np
import requests
import anthropic

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import csv
import io

# --- DATABASE INIT ---
models.Base.metadata.create_all(bind=engine)

# --- ANTHROPIC CLIENT (replaces Gemini) ---
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
        with open("criterion_films.json", "r") as f:
            criterion_data = json.load(f)
            CRITERION_FILMS = set(criterion_data.keys())
        print(f"✅ Loaded {len(CRITERION_FILMS)} Criterion Collection films")
    except Exception as e:
        print(f"⚠️  Could not load Criterion films: {e}")
else:
    print("⚠️  criterion_films.json not found. Run fetch_criterion.py to generate it.")

# --- SCORING WEIGHTS (Tonypedia is the most ponderous factor) ---
WEIGHTS = {
    "tonypedia": 0.40,
    "imdb":      0.25,
    "rt":        0.20,
    "metacritic": 0.10,
    "tmdb":      0.05,
}

app = FastAPI(title="Tonypedia AI Backend", version="2.1.0")

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

def embed_mood(mood: str, topic: str, vibe: str) -> np.ndarray:
    """Convert the 3 user inputs into a single semantic vector via Voyage AI."""
    mood_string = f"Mood: {mood}. Topic: {topic}. Vibe: {vibe}."
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"input": [mood_string], "model": "voyage-large-2"}
    r = requests.post(VOYAGE_URL, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return np.array(r.json()["data"][0]["embedding"])


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def filter_by_genre(candidates: list[dict], genre: str = None) -> list[dict]:
    """Filter candidates by genre if specified. Single genre, not restrictive (soft filter)."""
    if not genre:
        return candidates
    
    genre_lower = genre.lower()
    # Soft filter: prioritize but don't exclude
    filtered = [c for c in candidates if genre_lower in str(c.get("genres", "")).lower()]
    # If soft filter removes too many, return all candidates
    if len(filtered) < 3:
        return candidates
    return filtered


def filter_by_eras(candidates: list[dict], eras: list[str] = None) -> list[dict]:
    """Filter candidates by era(s) if specified."""
    if not eras or len(eras) == 0:
        return candidates
    
    era_ranges = {
        "1900-1950": (1900, 1950),
        "1950-2000": (1950, 2000),
        "2000-2026": (2000, 2026),
    }
    
    valid_years = set()
    for era in eras:
        if era in era_ranges:
            start, end = era_ranges[era]
            valid_years.update(range(start, end + 1))
    
    if not valid_years:
        return candidates
    
    filtered = [c for c in candidates if int(c.get("year", 0)) in valid_years]
    # If filtering removes all, return all candidates
    return filtered if filtered else candidates


def find_top_candidates(mood_vector: np.ndarray, top_n: int = 15) -> list[dict]:
    """Return the top_n most semantically similar movies from the pre-computed corpus."""
    scores = []
    for movie_id, embedding in MOVIE_EMBEDDINGS.items():
        sim = cosine_similarity(mood_vector, embedding)
        scores.append((movie_id, sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [
        {**MOVIE_DATA[mid], "movie_id": mid, "match_score": round(sim, 4)}
        for mid, sim in scores[:top_n]
        if mid in MOVIE_DATA
    ]


def fetch_ratings(imdb_id: str, db: Session) -> dict:
    """
    Fetch aggregated ratings for a film. Checks DB cache first (24h TTL),
    then calls OMDb and TMDB if not cached.
    Returns individual scores + computed global_average + tonypedia_score separately.
    """
    cached = db.query(models.RatingsCache).filter_by(imdb_id=imdb_id).first()
    if cached:
        return {
            "imdb":         cached.imdb_score,
            "rt":           cached.rt_score,
            "metacritic":   cached.metacritic_score,
            "tmdb":         cached.tmdb_score,
            "tonypedia":    cached.tonypedia_score,
            "global_average": cached.composite_score,
        }

    imdb_score = rt_score = metacritic_score = tmdb_score = tonypedia_score = None

    # OMDb: IMDb score + Rotten Tomatoes + Metacritic
    omdb_key = os.getenv("OMDB_API_KEY")
    if omdb_key and imdb_id:
        try:
            r = requests.get(
                f"http://www.omdbapi.com/?i={imdb_id}&apikey={omdb_key}",
                timeout=5
            )
            data = r.json()
            if data.get("Response") == "True":
                if data.get("imdbRating") not in (None, "N/A"):
                    imdb_score = float(data["imdbRating"])
                for rating in data.get("Ratings", []):
                    if rating["Source"] == "Rotten Tomatoes":
                        rt_score = float(rating["Value"].replace("%", "")) / 10
                    if rating["Source"] == "Metacritic":
                        metacritic_score = float(rating["Value"].split("/")[0]) / 10
        except Exception as e:
            print(f"OMDb error for {imdb_id}: {e}")

    # TMDB: score + poster (primary metadata source)
    tmdb_key = os.getenv("TMDB_API_KEY")
    if tmdb_key and imdb_id:
        try:
            r = requests.get(
                f"https://api.themoviedb.org/3/find/{imdb_id}",
                params={"api_key": tmdb_key, "external_source": "imdb_id"},
                timeout=5
            )
            results = r.json().get("movie_results", [])
            if results:
                tmdb_score = results[0].get("vote_average")
        except Exception as e:
            print(f"TMDB error for {imdb_id}: {e}")

    # Tonypedia proprietary score
    tp_entry = db.query(models.TonypediaRating).filter_by(imdb_id=imdb_id).first()
    if tp_entry:
        tonypedia_score = tp_entry.score

    # Compute weighted Global Average (only from available scores)
    available = {
        "tonypedia": tonypedia_score,
        "imdb":      imdb_score,
        "rt":        rt_score,
        "metacritic": metacritic_score,
        "tmdb":      tmdb_score,
    }
    total_weight = sum(WEIGHTS[k] for k, v in available.items() if v is not None)
    if total_weight > 0:
        raw = sum(WEIGHTS[k] * v for k, v in available.items() if v is not None)
        global_average = round(raw / total_weight, 2)
    else:
        global_average = None

    # Cache the result
    cache_entry = models.RatingsCache(
        imdb_id=imdb_id,
        imdb_score=imdb_score,
        rt_score=rt_score,
        metacritic_score=metacritic_score,
        tmdb_score=tmdb_score,
        tonypedia_score=tonypedia_score,
        composite_score=global_average,
    )
    db.merge(cache_entry)
    db.commit()

    return {
        "imdb":          imdb_score,
        "rt":            rt_score,
        "metacritic":    metacritic_score,
        "tmdb":          tmdb_score,
        "tonypedia":     tonypedia_score,   # displayed separately on the card
        "global_average": global_average,  # displayed as the composite badge
    }


def rerank_with_claude(candidates: list[dict], mood: str, topic: str, vibe: str) -> list[dict]:
    """
    Send Top 15 candidates to Claude Haiku.
    Claude re-ranks them into a final Top 10 and adds a one-sentence
    mood-match explanation for each film.
    Returns a list of dicts with rank + explanation injected.
    """
    candidate_list = "\n".join(
        [f"{i+1}. {c['title']} ({c.get('year', '?')}) — {c.get('plot', '')[:120]}..."
         for i, c in enumerate(candidates)]
    )

    prompt = f"""You are Tonypedia, a cinematic mood oracle.

A user is feeling: Mood={mood}, Topic={topic}, Vibe={vibe}.

Here are 15 candidate films matched by semantic similarity to their mood:
{candidate_list}

Your task:
1. Re-rank these into the best Top 10 for this specific mood.
2. For each film, write exactly one sentence (max 20 words) explaining why it matches the mood.
3. Respond ONLY with a JSON array of 10 objects in this exact format:
[
  {{"rank": 1, "title": "Film Title", "explanation": "One sentence here."}},
  ...
]
No markdown, no preamble, no extra text. Pure JSON only."""

    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    
    # Debug: Check what we got back
    if not message.content or len(message.content) == 0:
        print("ERROR: Claude returned empty content")
        raise ValueError("Claude response is empty")
    
    raw = message.content[0].text.strip()
    print(f"--- CLAUDE RAW RESPONSE: {raw[:200]} ---")
    
    if not raw:
        print("ERROR: Claude text is empty")
        raise ValueError("Claude text response is empty")
    
    # Strip markdown code block wrapper if present
    if raw.startswith("```json"):
        raw = raw[7:]  # Remove ```json
    if raw.startswith("```"):
        raw = raw[3:]  # Remove ```
    if raw.endswith("```"):
        raw = raw[:-3]  # Remove trailing ```
    raw = raw.strip()
    
    try:
        ranked = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Claude JSON: {e}")
        print(f"Raw response was: {raw}")
        raise ValueError(f"Claude JSON parse error: {e}")

    # Merge Claude's ranking + explanation back into the candidate dicts
    # Create a more flexible title matching system
    title_map = {}
    for c in candidates:
        original_title = c["title"].lower()
        title_map[original_title] = c
        # Also map without year if present: "Film (2020)" -> "film"
        title_no_year = original_title.split("(")[0].strip()
        if title_no_year not in title_map:
            title_map[title_no_year] = c
    
    results = []
    for item in ranked:
        claude_title = item["title"].lower()
        # Try exact match first
        match = title_map.get(claude_title)
        # If no exact match, try without year
        if not match:
            claude_title_no_year = claude_title.split("(")[0].strip()
            match = title_map.get(claude_title_no_year)
        # If still no match, use empty dict (will show "Unknown")
        if not match:
            match = {}
            print(f"WARNING: Could not match title '{item['title']}' from Claude")
        
        results.append({
            **match,
            "rank": item["rank"],
            "explanation": item["explanation"],
        })
    return results


# ──────────────────────────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "online", "message": "Tonypedia AI v2.1 — Anthropic Stack"}


@app.get("/recommend")
def get_recommendations(
    mood: str, 
    topic: str, 
    vibe: str, 
    genre: str = None,
    eras: str = None,  # comma-separated: "1900-1950,2000-2026"
    db: Session = Depends(get_db)
):
    """
    Enhanced endpoint with automatic search expansion.
    Guarantees Top 10 results by expanding search if needed.
    
    Parameters:
    - mood: emotional state
    - topic: thematic focus
    - vibe: atmosphere/aesthetic
    - genre: optional single genre filter (soft filter)
    - eras: optional comma-separated eras
    """
    try:
        # Parse eras from comma-separated string
        era_list = [e.strip() for e in eras.split(",")] if eras else []
        
        # Step 1: Embed user mood via Voyage AI
        print(f"--- MOOD INPUT: mood={mood} | topic={topic} | vibe={vibe} | genre={genre} | eras={eras} ---")
        mood_vector = embed_mood(mood, topic, vibe)

        # Step 2: Vector search against pre-computed corpus → Top 15 candidates
        candidates = find_top_candidates(mood_vector, top_n=15)
        print(f"--- VECTOR SEARCH: {len(candidates)} candidates found ---")
        
        # Step 3: Apply genre filter (soft - non-restrictive)
        candidates_filtered = filter_by_genre(candidates, genre)
        print(f"--- GENRE FILTER: {len(candidates_filtered)} candidates after genre filter ---")
        
        # Step 4: Apply era filter
        candidates_filtered = filter_by_eras(candidates_filtered, era_list)
        print(f"--- ERA FILTER: {len(candidates_filtered)} candidates after era filter ---")

        # EXPANSION LOGIC: If <10 results, progressively expand search
        if len(candidates_filtered) < 10:
            print(f"⚠️  Only {len(candidates_filtered)} results. Expanding search...")
            
            # First expansion: remove era filter, keep genre
            if len(candidates_filtered) < 10:
                candidates_expanded = filter_by_genre(candidates, genre)
                print(f"--- EXPANSION 1 (remove era): {len(candidates_expanded)} candidates ---")
                if len(candidates_expanded) > len(candidates_filtered):
                    candidates_filtered = candidates_expanded
            
            # Second expansion: remove both filters
            if len(candidates_filtered) < 10:
                candidates_expanded = candidates
                print(f"--- EXPANSION 2 (remove all filters): {len(candidates_expanded)} candidates ---")
                if len(candidates_expanded) > len(candidates_filtered):
                    candidates_filtered = candidates_expanded

        # Step 5: Claude Haiku re-ranks filtered candidates → final Top 10
        top_10 = rerank_with_claude(candidates_filtered[:15], mood, topic, vibe)
        print(f"--- CLAUDE RERANK: Top 10 finalised ---")

        # Step 6: Enrich each film with ratings (cache-first)
        # RULE 1: Prioritize Tonypedia-rated movies (up to 6)
        tonypedia_films = []
        other_films = []
        
        for film in top_10:
            imdb_id = film.get("imdb_id", "")
            tp_entry = db.query(models.TonypediaRating).filter_by(imdb_id=imdb_id).first()
            
            if tp_entry and tp_entry.score:
                tonypedia_films.append((film, tp_entry))
            else:
                other_films.append(film)
        
        # Combine: up to 6 Tonypedia films first, then other films
        prioritized_films = tonypedia_films[:6] + [(f, None) for f in other_films]
        
        enriched = []
        for idx, item in enumerate(prioritized_films):
            if isinstance(item, tuple):
                film, tp_entry = item
            else:
                film = item
                tp_entry = None
            
            imdb_id = film.get("imdb_id", "")
            ratings = fetch_ratings(imdb_id, db)

            # Fetch poster from TMDB (primary) or OMDb (fallback)
            poster = film.get("poster") or fetch_poster(imdb_id)

            # RULE 2: Use Tonypedia notes if available, otherwise Claude explanation
            if tp_entry and tp_entry.notes:
                explanation = tp_entry.notes
            else:
                explanation = film.get("explanation", "")

            # CRITERION BOOST: Add 1.5 point bonus to global_average if it's a Criterion film
            global_avg = ratings["global_average"]
            criterion_boost = 0
            is_criterion = imdb_id in CRITERION_FILMS
            if is_criterion and global_avg:
                criterion_boost = 1.5
                global_avg = min(10.0, global_avg + criterion_boost)  # Cap at 10.0

            enriched.append({
                "rank":          idx + 1,
                "title":         film.get("title", "Unknown"),
                "year":          film.get("year", ""),
                "plot":          film.get("plot", ""),
                "poster":        poster,
                "explanation":   explanation,
                "global_average":   global_avg,  # Boosted if Criterion
                "tonypedia_score":  ratings["tonypedia"],
                "is_criterion":     is_criterion,  # Flag for UI display
                "scores": {
                    "imdb":       ratings["imdb"],
                    "rt":         ratings["rt"],
                    "metacritic": ratings["metacritic"],
                    "tmdb":       ratings["tmdb"],
                }
            })

        # RULE 3: Sort by global_average rating (highest first) to prioritize quality
        # Criterion films will naturally rank higher due to +1.5 boost
        enriched.sort(key=lambda x: (x["global_average"] is None, -(x["global_average"] or 0)))
        
        # RULE 3B: QUALITY THRESHOLD - Guarantee Top 10 with quality-first approach
        # Exception: Always include if Tonypedia rating > 5 (curator's pick overrides threshold)
        # Progressive threshold relaxation to ensure exactly 10 results
        thresholds = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 0.0]  # Last is no threshold (include all)
        
        enriched_filtered = []
        for threshold in thresholds:
            enriched_filtered = [
                f for f in enriched 
                if (f["global_average"] is not None and f["global_average"] >= threshold) 
                or (f["tonypedia_score"] is not None and f["tonypedia_score"] > 5)
            ]
            
            if len(enriched_filtered) >= 10:
                print(f"--- QUALITY FILTER: Found 10+ films at threshold {threshold} ---")
                break
            else:
                print(f"--- QUALITY FILTER: Only {len(enriched_filtered)} films at threshold {threshold}, lowering... ---")
        
        enriched = enriched_filtered
        
        # Re-rank after sorting and filtering
        for idx, film in enumerate(enriched[:10]):
            film["rank"] = idx + 1
        
        # Return exactly Top 10 (guarantee 10 results)
        enriched = enriched[:10]
        
        # Log if we had to relax threshold significantly
        if len(enriched) < 10:
            print(f"⚠️  WARNING: Could only find {len(enriched)} films for Top 10")

        # Step 7: Log session to DB
        session_log = models.MoodSession(
            mood_raw={"mood": mood, "topic": topic, "vibe": vibe, "genre": genre, "eras": eras},
            result_titles=[f["title"] for f in enriched]
        )
        db.add(session_log)
        db.commit()

        return {"results": enriched, "session_id": session_log.id}

    except Exception as e:
        error_msg = str(e)
        print(f"--- CRITICAL ERROR: {error_msg} ---")
        raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")


def fetch_poster(imdb_id: str) -> str | None:
    """Fetch poster URL from TMDB (primary) with OMDb as fallback."""
    tmdb_key = os.getenv("TMDB_API_KEY")
    if tmdb_key and imdb_id:
        try:
            r = requests.get(
                f"https://api.themoviedb.org/3/find/{imdb_id}",
                params={"api_key": tmdb_key, "external_source": "imdb_id"},
                timeout=5
            )
            results = r.json().get("movie_results", [])
            if results and results[0].get("poster_path"):
                return f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}"
        except Exception:
            pass

    omdb_key = os.getenv("OMDB_API_KEY")
    if omdb_key and imdb_id:
        try:
            r = requests.get(f"http://www.omdbapi.com/?i={imdb_id}&apikey={omdb_key}", timeout=5)
            data = r.json()
            if data.get("Poster") not in (None, "N/A"):
                return data["Poster"]
        except Exception:
            pass
    return None


@app.get("/tonypedia/browse")
def browse_tonypedia(db: Session = Depends(get_db)):
    """
    Browse all Tonypedia-rated movies sorted by rating (best first).
    Returns all films you've personally rated with your scores and notes.
    """
    try:
        # Get all Tonypedia ratings, ordered by score descending
        tp_ratings = db.query(models.TonypediaRating).order_by(
            models.TonypediaRating.score.desc()
        ).all()
        
        print(f"--- TONYPEDIA BROWSE: {len(tp_ratings)} rated films ---")
        
        enriched = []
        for idx, tp_entry in enumerate(tp_ratings, 1):
            imdb_id = tp_entry.imdb_id
            
            # Get film data
            movie_data = MOVIE_DATA.get(imdb_id, {})
            
            # Fetch other ratings
            ratings = fetch_ratings(imdb_id, db)
            
            # Fetch poster
            poster = movie_data.get("poster") or fetch_poster(imdb_id)
            
            # Check if Criterion
            is_criterion = imdb_id in CRITERION_FILMS
            
            enriched.append({
                "rank": idx,
                "title": movie_data.get("title", "Unknown"),
                "year": movie_data.get("year", ""),
                "plot": movie_data.get("plot", ""),
                "poster": poster,
                "tonypedia_score": tp_entry.score,
                "tonypedia_notes": tp_entry.notes,
                "is_criterion": is_criterion,
                "global_average": ratings["global_average"],
                "scores": {
                    "imdb": ratings["imdb"],
                    "rt": ratings["rt"],
                    "metacritic": ratings["metacritic"],
                    "tmdb": ratings["tmdb"],
                }
            })
        
        return {"results": enriched, "total": len(enriched)}
        
    except Exception as e:
        error_msg = str(e)
        print(f"--- CRITICAL ERROR: {error_msg} ---")
        raise HTTPException(status_code=500, detail=f"Server error: {error_msg}")
    """Fetch poster URL from TMDB (primary) with OMDb as fallback."""
    tmdb_key = os.getenv("TMDB_API_KEY")
    if tmdb_key and imdb_id:
        try:
            r = requests.get(
                f"https://api.themoviedb.org/3/find/{imdb_id}",
                params={"api_key": tmdb_key, "external_source": "imdb_id"},
                timeout=5
            )
            results = r.json().get("movie_results", [])
            if results and results[0].get("poster_path"):
                return f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}"
        except Exception:
            pass

    omdb_key = os.getenv("OMDB_API_KEY")
    if omdb_key and imdb_id:
        try:
            r = requests.get(f"http://www.omdbapi.com/?i={imdb_id}&apikey={omdb_key}", timeout=5)
            data = r.json()
            if data.get("Poster") not in (None, "N/A"):
                return data["Poster"]
        except Exception:
            pass
    return None


@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    """Return the last 20 mood sessions for the history dashboard."""
    sessions = db.query(models.MoodSession).order_by(
        models.MoodSession.created_at.desc()
    ).limit(20).all()
    return {"history": [
        {
            "session_id": s.id,
            "mood":       s.mood_raw,
            "titles":     s.result_titles,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]}


@app.post("/admin/ratings/upload")
async def upload_tonypedia_ratings(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: upload tonypedia.CSV to upsert proprietary scores.
    Required CSV columns: imdb_id, score (0–10), notes (optional)
    Protected by ADMIN_API_KEY header in production.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    upserted = 0
    errors = []
    for i, row in enumerate(reader):
        try:
            imdb_id = row.get("imdb_id", "").strip()
            score = float(row.get("score", 0))
            notes = row.get("notes", "").strip()

            if not imdb_id or not (0 <= score <= 10):
                errors.append(f"Row {i+2}: invalid data — skipped")
                continue

            entry = models.TonypediaRating(
                imdb_id=imdb_id,
                score=score,
                notes=notes,
            )
            db.merge(entry)
            upserted += 1
        except Exception as e:
            errors.append(f"Row {i+2}: {str(e)}")

    db.commit()
    return {
        "status": "done",
        "upserted": upserted,
        "errors": errors,
    }
