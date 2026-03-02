from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class Movie(Base):
    """Original table — unchanged. Keeps backward compatibility."""
    __tablename__ = "movies"
    id     = Column(Integer, primary_key=True, index=True)
    title  = Column(String)
    year   = Column(String)
    plot   = Column(String)
    poster = Column(String)


class RatingsCache(Base):
    """
    Caches aggregated ratings per film (keyed by IMDb ID).
    Avoids hammering OMDb/TMDB on every request.
    TTL refresh is handled at the application layer (24h).
    """
    __tablename__ = "ratings_cache"
    id               = Column(Integer, primary_key=True, index=True)
    imdb_id          = Column(String, unique=True, index=True, nullable=False)
    imdb_score       = Column(Float, nullable=True)
    rt_score         = Column(Float, nullable=True)   # Rotten Tomatoes /10
    metacritic_score = Column(Float, nullable=True)   # Metacritic /10
    tmdb_score       = Column(Float, nullable=True)
    tonypedia_score  = Column(Float, nullable=True)
    composite_score  = Column(Float, nullable=True)   # Weighted Global Average
    cached_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TonypediaRating(Base):
    """
    Proprietary Tonypedia scores ingested from tonypedia.CSV.
    Matched to films via imdb_id for reliability across all external APIs.
    """
    __tablename__ = "tonypedia_ratings"
    id         = Column(Integer, primary_key=True, index=True)
    imdb_id    = Column(String, unique=True, index=True, nullable=False)
    score      = Column(Float, nullable=False)   # 0.0 – 10.0
    notes      = Column(String, nullable=True)   # Editorial context (optional)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MoodSession(Base):
    """
    Logs every user mood assessment and the Top 10 titles returned.
    Powers the history dashboard and future personalisation features.
    """
    __tablename__ = "mood_sessions"
    id            = Column(Integer, primary_key=True, index=True)
    mood_raw      = Column(JSON, nullable=False)    # {"mood": "...", "topic": "...", "vibe": "..."}
    result_titles = Column(JSON, nullable=True)     # ["Film A", "Film B", ...]
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
