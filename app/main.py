import os
import secrets
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException

from .assignment import suggerer_responsables
from .classifier import VERSION_MODELE, classifier
from .schemas import (
    ClassifyRequest,
    ClassifyResponse,
    SuggestAssigneeRequest,
    SuggestAssigneeResponse,
)


def verifier_cle(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Si AI_SERVICE_KEY est définie, Laravel doit l'envoyer dans l'en-tête X-API-Key."""
    attendue = os.getenv("AI_SERVICE_KEY")
    if not attendue:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, attendue):
        raise HTTPException(status_code=401, detail="Clé API invalide")


app = FastAPI(title="Service IA - gestion des tâches", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"statut": "ok", "version_modele": VERSION_MODELE}


@app.post("/classify", response_model=ClassifyResponse, dependencies=[Depends(verifier_cle)])
def classify(req: ClassifyRequest) -> ClassifyResponse:
    return classifier(req)


@app.post(
    "/suggest-assignee",
    response_model=SuggestAssigneeResponse,
    dependencies=[Depends(verifier_cle)],
)
def suggest_assignee(req: SuggestAssigneeRequest) -> SuggestAssigneeResponse:
    return suggerer_responsables(req)
