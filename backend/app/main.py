from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.shared.rdf_store import store
from app.shared.recherche.analyse import nlp
from app.shared.recherche.router import router as search_router
from app.shared.recherche.vocabulaire import vocabulaire
from app.features.territoires_acteurs.router import router as territories_actors_router
from app.features.maintenance.router import router as maintenance_router
from app.features.stockage.router import router as storage_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Chargement de l'ontologie, raisonnement et modèle spaCy dès le démarrage.
    store()
    vocabulaire()
    nlp()
    yield


app = FastAPI(title="EnergyHomeOnto API", version="0.2.0", lifespan=lifespan)
app.include_router(search_router, prefix="/api")
app.include_router(territories_actors_router, prefix="/api")
app.include_router(maintenance_router, prefix="/api")
app.include_router(storage_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str | int]:
    current = store()
    return {"status": "ok", "triplets_asserts": len(current.asserted), "triplets_inferes": len(current.inferred)}
