# findyourloss · Campus Lost & Found

“One campus. One platform. Every lost item finds its way home.” findyourloss pairs campus lost and found reports using item category, colour, brand, campus location, report time, and description.

## Run locally

Requires Python 3.11+ and Node.js 20+. From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:USE_MOCK_DB="true"
uvicorn main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. On first start the backend creates hidden sample candidates so a new report can demonstrate matching immediately. Sample candidates are excluded from Home, report lists, stats, and Insights; only real submissions appear there. They are labelled as demo suggestions and cannot be chatted with or marked reunited. With `USE_MOCK_DB=true`, all data clears when you stop the backend. For persistent MongoDB, unset `USE_MOCK_DB` and set `MONGO_URI` (defaults to `mongodb://localhost:27017`). Set `VITE_API_URL` when the API is hosted elsewhere. API documentation is at http://localhost:8000/docs.

## API

- `POST /api/reports/lost` and `POST /api/reports/found` — create a report with optional building/floor/room and map pin coordinates, then return ranked open opposite-type matches. Pass `force: true` to submit a likely duplicate.
- `GET /api/reports?type=&status=&place=&limit=` and `GET /api/reports/{report_id}` — list or read reports.
- `GET /api/matches/{report_id}` — refresh matches.
- `GET/POST /api/reports/{report_id}/chat` — read/send meetup messages with a matched opposite report; messages remain available in Chat History. `POST /api/reports/{report_id}/reunite` with `{"matched_with":"R002"}` marks both reports reunited after the handoff.
- `POST /api/upload` — save an image in `backend/uploads`.
- `GET /api/stats`, `/api/insights`, `/api/locations`, `/api/buildings`, `/api/alerts?report_id=R001` — university-wide totals, location/day analytics, GLA map pins, and high probability matches.

## Campus location pins

The campus map is centered on the GLA University pin from the supplied Google Maps link (`27.60486, 77.5970753`). Nearby building and campus-area coordinates are approximate outdoor pins estimated from the supplied map image. The form allows a manual map click to adjust a pin; classroom-level indoor positions still need a verified floor plan.

## Matching

BLUE combines normalized category (25%), colour (15%), brand (10%), location (15%), time (10%), and description (25%). Category mismatch caps the score at 35. Descriptions use RapidFuzz token matching blended with cached pre-trained `all-MiniLM-L6-v2` embeddings when sentence-transformers is installed; otherwise RapidFuzz remains active and logs the fallback. The optional embedding package/model is intentionally not in the minimal requirements, keeping setup quick and the app runnable offline.

## Two-minute judge demo

1. Open Home and show the clean dashboard with zero old reports.
2. Open Report Item and submit a lost “Navy Bottle”, colour “Navy”, brand “Milton”, and place “Library”.
3. Submit the corresponding found report in another browser/session; show the match and its reason chips.
4. Open the chat from the match card, agree on a public campus meetup spot, then confirm the handoff.
5. Open Insights to see counts update from reports made during this run.

Seed generation is idempotent and produces exactly 150 fictional reports without personal identifiers. The matcher unit cases are in `backend/test_matching.py` (`pytest`).

## Current scope

Included: FastAPI API, MongoDB/mongomock storage, optional seed data, duplicate warning, matching, meetup chat, handoff confirmation, image upload, stats and analytics, responsive React dashboard, charts, map, report form, and matching results. Optional sentence-transformer embeddings fall back cleanly to RapidFuzz.
