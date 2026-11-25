# BLUE · Campus Lost & Found Intelligence

“One campus. One platform. Every lost item finds its way home.” BLUE pairs campus lost and found reports using item category, colour, brand, campus location, report time, and description.

## Run locally

Requires Python 3.11+ and Node.js 20+. From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:USE_MOCK_DB="true"
python seed.py
uvicorn main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Mock DB data lives in memory and the API process seeds itself on startup; `python seed.py` is also available for direct seed verification or MongoDB seeding. For persistent MongoDB, unset `USE_MOCK_DB` and set `MONGO_URI` (defaults to `mongodb://localhost:27017`). Set `VITE_API_URL` when the API is hosted elsewhere. API documentation is at http://localhost:8000/docs.

## API

- `POST /api/reports/lost` and `POST /api/reports/found` — create a report and return ranked open opposite-type matches. Pass `force: true` to submit a likely duplicate.
- `GET /api/reports?type=&status=&place=&limit=` and `GET /api/reports/{report_id}` — list or read reports.
- `GET /api/matches/{report_id}` — refresh matches.
- `POST /api/reports/{report_id}/reunite` with `{"matched_with":"R002"}` — mark both reports reunited.
- `POST /api/upload` — save an image in `backend/uploads`.
- `GET /api/stats`, `/api/insights`, `/api/locations`, `/api/alerts?report_id=R001` — dashboard, analytics, locations, and high probability matches.

## Matching

BLUE combines normalized category (25%), colour (15%), brand (10%), location (15%), time (10%), and description (25%). Category mismatch caps the score at 35. Descriptions use RapidFuzz token matching blended with cached pre-trained `all-MiniLM-L6-v2` embeddings when sentence-transformers is installed; otherwise RapidFuzz remains active and logs the fallback. The optional embedding package/model is intentionally not in the minimal requirements, keeping setup quick and the app runnable offline.

## Two-minute judge demo

1. Open Home and point out the seeded activity, report statistics, and OpenStreetMap hotspot markers.
2. Open Report Item. Submit a lost “Navy Bottle”, colour “Navy”, brand “Milton”, place “Library”, and a time close to now.
3. Show the ranked Blue Water Flask candidate, score, and reason chips on Matching Results.
4. Mark the candidate as reunited and return Home to show the updated counts.
5. Open Insights to show item frequency, location and day charts, report status, and hotspot table.

Seed generation is idempotent and produces exactly 150 fictional reports without personal identifiers. The matcher unit cases are in `backend/test_matching.py` (`pytest`).

## Current scope

Included: FastAPI API, MongoDB/mongomock storage, seed data, duplicate warning, matching, reunite flow, image upload, stats and analytics, responsive React dashboard, charts, map, report form, and matching results. The alert endpoint is present; automatic navbar polling/toasts are not wired yet. Optional sentence-transformer embeddings fall back cleanly to RapidFuzz.
