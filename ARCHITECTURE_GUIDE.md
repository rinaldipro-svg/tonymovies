# Tonypedia v3.0.0 — Key Architectural Changes Quick Reference

## Before vs After

### OLD (v2.1.0) — Broken 🔴
```
1. embed_mood_with_award_context()
   → Injects "Oscar/Palme d'Or/Criterion films are excellent" into embedding
   → Pollutes semantic vector space
   → Degrades search quality for non-award films

2. Vector search top 15
   → Too small a pool for Claude to choose from
   → Likely misses good matches

3. Process:
   - Vector search top 15
   - Filter by genre
   - Claude ranks (10 results)
   - TIER SYSTEM SORT (overrides Claude!)
   - Quality threshold filter
   - Return 10

4. Problems:
   - Tier sort AFTER Claude undoes Claude's work
   - Quality threshold rejects valid results  
   - No guaranteed Tonypedia representation
   - No guaranteed award representation
   - Criterion films get +1.5 score boost (score manipulation)
   - Vector search polluted by award context
```

### NEW (v3.0.0) — Correct ✅
```
PHASE 1: Candidate Pool Assembly (~50-55 films)
  1. build_embedding_query(mood, topic, vibe, genre, era)
     → Maps labels to rich embedding text
     → NO award language (embedding stays pure)
     → Example: "A film that feels {mood_embedding}. It explores themes of {topic_embedding}..."
  
  2. embed_text(query_text) via Voyage AI
     → Clean semantic embedding
     → Represents user intent, not award preferences
  
  3. Vector search top 40
     → Large pool for enrichment
     → Use np.argpartition for O(n) performance
  
  4. Soft filters (genre, era)
     → Non-destructive
     → Fall back to unfiltered if pool < 30
  
  5. Inject Tonypedia films
     → Query ALL Tonypedia films from DB
     → Compute similarity to user query
     → Take top 8 most relevant NOT already in pool
     → Guarantees personal curation represented
  
  6. Inject award films
     → Find all Oscar/Palme/Criterion films
     → Compute similarity to user query
     → Take top 8 most relevant NOT already in pool
     → Guarantees critical excellence represented
  
  7. Deduplicate by imdb_id
     → Result: ~40-55 unique films

PHASE 2: Claude Re-Ranking (The Curator)
  1. Build candidate_block showing all films + tags
     - TONYPEDIA(score): Tonypedia-rated films with their score
     - OSCAR: Oscar winners
     - PALME D'OR: Palme d'Or winners  
     - CRITERION: Criterion Collection
     - Average rating from cache
  
  2. Claude prompt with hard rules:
     - MUST return exactly 10
     - MUST include min 3 Tonypedia films
     - MUST include min 3 award films (Oscar/Palme/Criterion)
     - Films can count toward BOTH minimums if tagged with both
     - RANKING PRIORITY: Mood match is KING. Untagged well-matching film > tagged poorly-matching film
     - Tags are tiebreakers, not overrides
  
  3. Claude returns: 10 films with rank + reason
  
  4. JSON parsing + retry logic
     - Strip markdown if needed
     - If parse fails once, retry with stricter prompt
     - If fails again, fall back to similarity-based ranking

PHASE 3: Enforcement & Enrichment  
  1. Map Claude's titles back to pool (fuzzy matching)
  
  2. Enforce hard rules by SURGICAL REPLACEMENT:
     - Count Tonypedia films in top 10
     - If < 3, find replacement from remaining pool, replace lowest-ranked non-essential film
     - Never replace a film that's sole contributor to another rule
     - Same for award films
  
  3. Enrich each film:
     - Fetch poster if missing
     - Batch fetch all ratings (1 DB query)
     - Compute is_tonypedia, is_criterion, is_oscar_winner, is_oscar_nominated, is_palme_dor_winner
     - Explanation from Claude or Tonypedia notes (prefer notes if available)
  
  4. Verify exactly 10 results

Result: 10 perfectly ranked films with full metadata
```

## Dual-Layer Criteria (The Secret Weapon)

### The Problem
Voyage AI produces dramatically better embeddings when fed rich, evocative text rather than single words. But users need simple, short labels in the UI.

### The Solution
Every criterion has TWO representations:

| Layer | Example | Used For |
|-------|---------|----------|
| **UI Label** | "Thrilling" | User sees and selects |
| **Embedding Text** | "heart-pounding suspense, edge-of-seat tension, adrenaline..." | Voyage AI embedding |

Frontend sends labels. Backend maps to embedding text before creating vector. This decoupling is fundamental to the entire engine's precision.

## Criteria Maps (Implemented)

```python
MOOD_MAP = {
    "Thrilling": "heart-pounding suspense, edge-of-seat tension, adrenaline...",
    "Heartwarming": "emotional comfort, uplifting human connection, feel-good catharsis...",
    # ... 10 more
}

TOPIC_MAP = {
    "Identity & self-discovery": "searching for identity, understanding the self...",
    "Family & relationships": "family bonds and fractures, generational conflict...",
    # ... 13 more
}

VIBE_MAP = {
    "Cinematic & epic": "sweeping colossal scale, grand orchestral score...",
    "Raw & gritty": "gritty cinema verité, handheld camera, natural lighting...",
    # ... 6 more
}

ERA_MAP = {
    "Pre-1960 (Golden Age)": "classic golden age Hollywood cinema, black and white...",
    # ... with ERA_YEAR_RANGES for soft filtering
}

GENRES = ["Drama", "Comedy", "Thriller", ...] # 14 standard genres
```

## Key Differences Explained

| Aspect | v2.1.0 | v3.0.0 |
|--------|--------|--------|
| Embedding | Award-context polluted | Pure user intent |
| Vector pool size | 15 | 40 + injections |
| Tonypedia guarantee | None | Top 8 injected |
| Award guarantee | None | Top 8 injected |
| Ranking source | Tier sort (after Claude) | Claude (never re-sorted) |
| Hard rule enforcement | N/A (tier sort was the system) | Surgical replacement |
| Quality threshold | Yes (rejects films) | No (Claude already filtered) |
| Criterion boost | +1.5 to score | Tags only (no score boost) |
| Final count | Variable | Exactly 10 (always) |

## Performance
- Vector search: top 40 using np.argpartition (O(n))
- Ratings: 1 DB query for whole pool (batch fetch)
- Tonypedia entries: 1 DB query for whole pool (batch fetch)
- Full pipeline: < 3 seconds (excluding network calls)

## Error Handling
1. Claude JSON parse fails → Retry with stricter prompt
2. Retry fails → Fall back to similarity-based ranking
3. Empty candidate pool → Return empty results gracefully
4. Missing poster → Leave as None
5. Missing year → Include in era filter anyway

## Checklist: What Got Removed ❌
- `embed_mood_with_award_context()` - award injection was destructive
- Tier system sort after Claude - was undoing curation
- Quality threshold filtering - Claude already filters
- `+1.5` Criterion score boost - no score manipulation
- `WEIGHTS` dictionary - unused old system

## Checklist: What Gets Kept ✅
- All non-recommend endpoints: `/`, `/favicon.ico`, `/tonypedia/browse`, `/tonypedia/rate`, `/tonypedia/import`
- Data loading: embeddings, JSON datasets
- Helper functions: `cosine_similarity()`, `fetch_ratings()`, `batch_fetch_ratings()`, `fetch_poster()`
- Filter functions: `filter_by_genre()`, `filter_by_era()` (updated for new era labels)

## Testing the New System

### Test Case 1: Tonypedia Hard Rule
```
Request: mood that yields <3 Tonypedia films
Expected: Hard rule enforcer injects Tonypedia films to reach 3 minimum
Verify: Top 10 has at least 3 Tonypedia films with scores
```

### Test Case 2: Award Hard Rule
```
Request: mood that yields <3 award films
Expected: Hard rule enforcer injects award films to reach 3 minimum  
Verify: Top 10 has at least 3 award films (Oscar/Palme/Criterion)
```

### Test Case 3: Claude Ranking Preserved
```
Request: any mood
Expected: Claude's rank order preserved (no tier sort after)
Verify: Mood-matching untagged films ranked above poorly-matching tagged films
```

### Test Case 4: Fallback Pool
```
Request: mood + genre + era that yields very small filtered pool
Expected: System falls back to unfiltered vector pool
Verify: Returns 10 results despite restrictive filters
```
