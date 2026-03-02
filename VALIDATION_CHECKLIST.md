# Tonypedia v3.0.0 — Validation & Testing Checklist

## Code Quality ✅
- [x] No Python syntax errors (verified by Pylance)
- [x] All imports present and used
- [x] No undefined variables
- [x] No circular imports
- [x] Database operations optimized (batch queries)
- [x] All old broken code removed
- [x] All endpoints preserved (except /recommend rewritten)

## Specification Compliance ✅

### Dual-Layer Criteria
- [x] MOOD_MAP has 12 entries (label → embedding text)
- [x] TOPIC_MAP has 15 entries (label → embedding text)
- [x] VIBE_MAP has 8 entries (label → embedding text)
- [x] ERA_MAP has 5 entries (label → embedding text)
- [x] ERA_YEAR_RANGES provides year ranges for filtering
- [x] GENRES list has 14 standard options
- [x] Embedding text is semantically rich (not single words)
- [x] Embedding text does NOT contain award language

### Core Functions
- [x] `build_embedding_query()` - builds clean query without award context
- [x] `embed_text()` - calls Voyage AI directly
- [x] `cosine_similarity()` - preserved from v2.1.0
- [x] `filter_by_genre()` - soft filter with fallback
- [x] `filter_by_era()` - uses ERA_YEAR_RANGES for year-based filtering
- [x] `batch_fetch_ratings()` - single DB query for pool
- [x] `fetch_poster()` - preserved from v2.1.0
- [x] `fuzzy_match_title()` - NEW for Claude title mapping

### Phase 1: Candidate Pool Assembly
- [x] Query text built from dual-layer criteria
- [x] Voyage AI embedding produced
- [x] Top 40 films retrieved (not 15)
- [x] Soft genre filter applied (non-destructive)
- [x] Soft era filter applied (non-destructive)
- [x] Fallback to unfiltered if filtered pool < 30
- [x] Tonypedia films queried from DB
- [x] Top 8 most relevant Tonypedia films injected
- [x] Award films queried (Oscar/Palme/Criterion)
- [x] Top 8 most relevant award films injected
- [x] Deduplication by imdb_id
- [x] Final pool size logged (~40-55 films)

### Phase 2: Claude Re-Ranking
- [x] Candidate block formatted: "idx. title (year) genre [tags] — Avg: x/10"
- [x] Tags formatted: TONYPEDIA(score), OSCAR, PALME D'OR, CRITERION
- [x] Claude prompt states 5 HARD RULES clearly
- [x] Claude prompt states 5 SOFT RULES clearly
- [x] Claude prompt emphasizes "Mood/criteria match is KING"
- [x] Claude prompt specifies tags are tiebreakers, not overrides
- [x] Claude uses model "claude-haiku-4-5-20251001"
- [x] max_tokens set to 1024
- [x] JSON response format specified in prompt
- [x] Markdown fence stripping implemented
- [x] Parse failure triggers retry with stricter prompt
- [x] Retry failure falls back to similarity-based ranking

### Phase 3: Enforcement & Enrichment
- [x] Claude titles mapped back to pool with fuzzy matching
- [x] Tonypedia hard rule (min 3) enforced
- [x] Award hard rule (min 3) enforced
- [x] Enforcement uses surgical replacement (not re-sorting)
- [x] Never replaces sole representative of another rule
- [x] Films enriched with: title, year, plot, poster
- [x] Films enriched with: explanation, global_average, tonypedia_score
- [x] Films enriched with: is_tonypedia, is_criterion, is_oscar_winner, is_oscar_nominated, is_palme_dor_winner
- [x] Films enriched with: individual scores (imdb, rt, metacritic, tmdb)
- [x] Films enriched with: rank (1-10), imdb_id
- [x] Exactly 10 results returned
- [x] Session logged to MoodSession table

### API Behavior
- [x] `/recommend` accepts mood, topic, vibe (required)
- [x] `/recommend` accepts genre, era (optional)
- [x] All parameters are strings
- [x] Returns JSON with "results" (array of 10) and "session_id"
- [x] Other endpoints unchanged: `/`, `/favicon.ico`, `/tonypedia/browse`, `/tonypedia/rate`, `/tonypedia/import`

## Code Cleanup ✅

### Removed (Old, Broken Code)
- [x] `embed_mood_with_award_context()` function deleted
- [x] TIER SYSTEM SORT logic deleted
- [x] Quality threshold filtering deleted
- [x] Criterion `+1.5` score boost deleted
- [x] WEIGHTS dictionary deleted
- [x] No re-sorting after Claude's ranking

### Preserved (Working Code)
- [x] `cosine_similarity()` function
- [x] `filter_by_genre()` updated but preserved
- [x] `filter_by_era()` updated to use ERA_YEAR_RANGES
- [x] `batch_fetch_ratings()` optimization
- [x] `fetch_poster()` function
- [x] All data loading code
- [x] All other endpoints

## Performance ✅
- [x] Vector search uses np.argpartition (O(n))
- [x] Ratings fetched in single batch DB query
- [x] Tonypedia entries fetched in single batch DB query
- [x] No N+1 query patterns
- [x] Similarity scores stored and reused
- [x] Expected runtime: < 3 seconds (excluding network)

## Error Handling ✅
- [x] Full pipeline in try/except block
- [x] Detailed logging at each phase
- [x] Empty candidate pool detected
- [x] Claude JSON parse failure triggers retry
- [x] Retry failure falls back to similarity ranking
- [x] Missing poster handled gracefully (None)
- [x] Missing year handled gracefully (included in filters anyway)
- [x] HTTPException raised with 500 + error message

## Integration Tests (Run These)

### Test 1: Vector Search Upper Bound
```
Verify: Vector search retrieves exactly 40 films (or fewer if corpus < 40)
Check logs for: "✅ Vector search: X films from top 40"
```

### Test 2: Tonypedia Injection
```
Setup: Request a mood that yields <3 Tonypedia films in vector search
Verify: Final results include at least 3 Tonypedia films
Check logs for: "✅ Injected X Tonypedia films"
```

### Test 3: Award Injection
```
Setup: Request a mood that yields <3 award films in vector search
Verify: Final results include at least 3 award films
Check logs for: "✅ Injected X award films"
```

### Test 4: Hard Rule Enforcement
```
Setup: Request resulting in <3 Tonypedia + <3 award initially
Verify: Hard rules enforced (surgical replacement, not re-sort)
Check: Top 10 ranking preserved (mood match not overridden)
Check logs for: "Hard rules enforced: X Tonypedia, Y award"
```

### Test 5: Fallback Pool
```
Setup: Request with genre + era both specified very restrictively
Verify: System doesn't crash, returns 10 results
Check logs for: "⚠️  Pool too small after soft filters... falling back"
```

### Test 6: Claude Ranking Preserved
```
Verify: Untagged but mood-matching films ranked above tagged poorly-matching films
Check: Explain why rankings make sense (mood-focused, not award-focused)
```

### Test 7: Poster Fetching
```
Verify: Films with missing posters don't crash
Check: Poster = None handled gracefully
```

### Test 8: Fuzzy Title Matching
```
Setup: Claude returns slightly misspelled title (unlikely but possible)
Verify: Fuzzy matcher finds correct film
Check logs for: successful or fallback matching
```

## API Response Format Validation ✅

Expected structure for each film in results array:
```json
{
  "rank": 1,
  "title": "Film Title",
  "year": "2020",
  "plot": "Plot summary...",
  "poster": "https://...",
  "explanation": "Why this matches the mood",
  "global_average": 8.2,
  "tonypedia_score": 8.5,
  "is_tonypedia": true,
  "is_criterion": false,
  "is_oscar_winner": true,
  "is_oscar_nominated": true,
  "is_palme_dor_winner": false,
  "imdb_id": "tt1234567",
  "scores": {
    "imdb": 8.1,
    "rt": 82,
    "metacritic": 78,
    "tmdb": 8.2
  }
}
```

Fields to verify:
- [x] rank is exactly 1-10 (no duplicates)
- [x] title is non-empty string
- [x] year is string or empty
- [x] plot is string or empty
- [x] poster is string URL or null
- [x] explanation is string (from Claude or Tonypedia notes)
- [x] global_average is float or null
- [x] tonypedia_score is float or null
- [x] Boolean flags are true/false
- [x] imdb_id is non-empty string
- [x] scores object has 4 fields, each float or null
- [x] Array length is exactly 10

## Logging Verification ✅

Expected log outputs (in order):
```
▶️  RECOMMEND REQUEST: mood=... | topic=... | vibe=... | genre=... | era=...

🔍 PHASE 1: Building candidate pool...
   Embedding query: ...
   ✅ Query embedded
   ✅ Vector search: X films from top 40
   ✅ Genre filter: Y films
   ✅ Era filter: Z films
   ✅ Injected W Tonypedia films
   ✅ Injected V award films
   ✅ Deduped: U unique films in candidate pool

🤖 PHASE 2: Claude re-ranking...
   ✅ Claude responded
   ✅ Claude ranked N films

📋 PHASE 3: Enforcement & enrichment...
   ✅ Mapped M Claude films back to pool
   Current: L Tonypedia, K award films
   ✅ Hard rules enforced: 3+ Tonypedia, 3+ award
   ✅ Enriched T films with full metadata

✅ RECOMMEND COMPLETE: 10 films returned
```

## Edge Cases to Test

1. **No Tonypedia ratings exist**
   - [ ] System still works
   - [ ] No error on Tonypedia injection

2. **No award films match mood**
   - [ ] Hard rule enforcement injects them anyway
   - [ ] Lowest-ranked films replaced

3. **Corpus very small (< 40 films)**
   - [ ] argpartition handles gracefully
   - [ ] Returns all available films

4. **All films in corpus match mood**
   - [ ] Top 40 still selected correctly
   - [ ] Pool size capped at reasonable number

5. **Genre filter removes all films**
   - [ ] Fallback to unfiltered triggered
   - [ ] Returns results anyway

6. **Era filter removes all films**
   - [ ] Fallback to unfiltered triggered
   - [ ] Returns results anyway

7. **Claude API fails**
   - [ ] Retry triggered
   - [ ] Falls back to similarity ranking

8. **Ratings DB empty**
   - [ ] global_average stays None
   - [ ] No error thrown

9. **Missing TMDB credit**
   - [ ] fetch_poster returns None
   - [ ] No error thrown

10. **Duplicate imdb_ids in candidate pool**
    - [ ] Deduped to single entry
    - [ ] Later entry kept (deterministic)

## Sign-Off Checklist

- [ ] All code changes reviewed
- [ ] Syntax validated (no Python errors)
- [ ] All 6 API endpoints working
- [ ] Phase 1 candidate pool assembly verified
- [ ] Phase 2 Claude re-ranking verified
- [ ] Phase 3 hard rule enforcement verified
- [ ] Metadata enrichment complete
- [ ] Edge cases tested
- [ ] Logging is comprehensive and helpful
- [ ] Performance acceptable (< 3s excluding network)
- [ ] Documentation complete (REWRITE_SUMMARY.md, ARCHITECTURE_GUIDE.md)
- [ ] Ready for production deployment

---

**Version**: 3.0.0  
**Rewrite Date**: March 1, 2026  
**Status**: ✅ Complete and Ready for Testing
