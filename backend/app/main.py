from fastapi import FastAPI

from app.shared.recherche.router import router as search_router
from app.features.territoires_acteurs.router import router as territories_actors_router

app = FastAPI(title="EnergyHomeOnto API", version="0.1.0")
app.include_router(search_router, prefix="/api")
app.include_router(territories_actors_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
