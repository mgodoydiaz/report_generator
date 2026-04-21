from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import pipelines, specs, dimensions, metrics, indicators, results
from backend.routers import auth, users, superadmin, organizations
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

@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
