from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import pipelines, specs, dimensions, metrics, indicators, results

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
