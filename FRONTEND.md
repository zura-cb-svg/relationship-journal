# Between — Director’s Cut

A redesigned, same-origin frontend for the existing Relationship Journal FastAPI project. AI-assisted portfolio work; not a production security certification.

## Start the full-stack app

Extract this archive into the existing project root (the directory with `main.py`, `routers/`, and `.env`). The files replace the earlier frontend only; existing API, migrations and data are untouched. Start your existing PostgreSQL and Redis containers, activate your Python environment, and run:

```powershell
docker start auth-drill-1-db-1 relationship-redis
python -m uvicorn serve_frontend:app --port 8002 --no-access-log
```

Open http://127.0.0.1:8002. Use the same origin for all API calls. Never share or commit `.env`. The separate downloadable preview HTML uses fictional data and does not require the API, external network access, or paid services.

## Visual engine

The original two-ribbon sculpture is defined by parametric geometry and GLSL shaders in `frontend/cinema.js`. Native WebGL continuously renders the shape, lighting, camera, scroll-linked morph, and mouse response. Resolution and mesh density are bounded for smaller screens. If WebGL is unavailable, 108 original rendered frames are distributed across 12 WebP atlases; adjacent frames are interpolated on a 2D canvas and nearby sheets are decoded ahead of the scroll position. The atlas fallback does not perform the full real-time 3D camera rotation on pointer movement. Reduced-motion mode presents all chapters as readable static sections. Native HTML, CSS and JavaScript; no npm, remote fonts, CDN or paid APIs.

## Application

Existing same-origin API adapter and fictional demo store retained: registration, login, restoration, refresh rotation, logout, relationship and journal CRUD, search/filter/pagination, dashboard counts, export and password-confirmed account deletion. Access tokens remain in memory; the API controls the HttpOnly refresh cookie. No journal data is sent to external services. The app is a portfolio project; use fictional demo data, not sensitive real information, when showcasing it.

## Checks and limitations

The GLSL vertex and fragment shaders were compiled and linked against OpenGL ES using a local software renderer; all 108 atlas frames were rendered using those shaders. Chromium's environment did not expose WebGL, so browser interactions exercised the atlas fallback rather than the hardware WebGL path. Chromium checks covered the three chapters, mobile viewport, reduced-motion layout, demo entry/relationship creation, and mock authentication requests. Actual GPU frame rate, iPhone Safari and real backend integration must still be tested on the target devices. Prior backend CI success (39 tests) precedes this UI package. No deployment or Git push was performed. The optional Docker entry point is retained but not newly tested. No spending or paid services were used.
