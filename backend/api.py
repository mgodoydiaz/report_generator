from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import workflows, templates, dimensions, metrics

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
app.include_router(workflows.router)
app.include_router(templates.router)
app.include_router(dimensions.router)
app.include_router(metrics.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
