from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.routers import pipelines, specs, dimensions, metrics, indicators, results
from backend.routers import auth, users, superadmin, organizations
from backend.routers import reports as reports_v2
from backend.routers import tables
from backend.database import init_db

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Rutas
app.include_router(pipelines.router)
app.include_router(specs.router)
app.include_router(dimensions.router)
app.include_router(metrics.router)
app.include_router(indicators.router)
app.include_router(results.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(superadmin.router)
app.include_router(organizations.router)
app.include_router(reports_v2.router)
app.include_router(tables.router)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Report Generator API</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 560px; margin: 10vh auto; padding: 0 24px; color: #1f2937; }}
  h1 {{ margin: 0 0 8px; font-size: 1.5rem; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px;
            background: #10b981; color: #fff; font-size: 0.85rem; font-weight: 600; }}
  dl {{ margin: 24px 0; display: grid; grid-template-columns: max-content 1fr;
        gap: 8px 16px; font-size: 0.95rem; }}
  dt {{ color: #6b7280; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px;
          font-size: 0.85rem; }}
</style>
</head>
<body>
  <h1>Report Generator API</h1>
  <span class="badge">online</span>
  <dl>
    <dt>Servicio</dt><dd>Report Generator API</dd>
    <dt>Estado</dt><dd>online</dd>
    <dt>Docs</dt><dd><a href="/docs">/docs</a> &middot; <a href="/redoc">/redoc</a></dd>
    <dt>Timestamp</dt><dd><code>{timestamp}</code></dd>
  </dl>
</body>
</html>"""


@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
