// ─── API CONFIGURATION ────────────────────────────────────────────────────────
// Production: Railway backend
// To test locally, swap to your local FastAPI server (e.g. http://192.168.x.x:8000)

export const API_URL = "https://tonypediabackend-production.up.railway.app";

// Request timeout in milliseconds
// Claude Haiku + Voyage AI embedding takes ~15–25s on first call
export const API_TIMEOUT = 60000;

// App version — update when deploying new builds
export const APP_VERSION = "2.1.0";

// Content modes — ready for Music and Books in future phases
export const MODES = {
  MOVIES: 'movies',
  MUSIC:  'music',   // Phase 2
  BOOKS:  'books',   // Phase 3
};

export const ACTIVE_MODE = MODES.MOVIES;
