from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Priorite = Literal["normal", "important", "urgent"]


class Departement(BaseModel):
    id: int
    nom: str
    description: Optional[str] = None


class TacheIn(BaseModel):
    titre: str = Field(min_length=1)
    description: Optional[str] = None
    priorite: Optional[Priorite] = None
    departement_id: Optional[int] = None
    # Optionnelle : la colonne d'échéance est en cours de conception côté Laravel
    date_echeance: Optional[date] = None


# ---------- /classify ----------

class ClassifyRequest(BaseModel):
    tache: TacheIn
    departements: list[Departement] = []
    # Pour les tests ; par défaut, la date du jour
    date_reference: Optional[date] = None


class PrioriteSuggestion(BaseModel):
    valeur: Priorite
    confiance: float
    raison: str


class DepartementSuggestion(BaseModel):
    departement_id: Optional[int]
    confiance: float
    raison: str


class ClassifyResponse(BaseModel):
    version_modele: str
    priorite: PrioriteSuggestion
    departement: Optional[DepartementSuggestion] = None


# ---------- /suggest-assignee ----------

class Candidat(BaseModel):
    id: int
    nom: str
    departement_id: Optional[int] = None
    # Tâches en_attente + en_cours actuellement assignées (calculé par Laravel)
    charge_en_cours: int = Field(default=0, ge=0)
    # Parmi elles, celles de priorité urgent
    charge_urgente: int = Field(default=0, ge=0)
    actif: bool = True


class SuggestAssigneeRequest(BaseModel):
    tache: TacheIn
    candidats: list[Candidat] = Field(min_length=1)
    limite: int = Field(default=3, ge=1, le=10)


class AssigneeSuggestion(BaseModel):
    utilisateur_id: int
    nom: str
    score: float
    raison: str


class SuggestAssigneeResponse(BaseModel):
    version_modele: str
    suggestions: list[AssigneeSuggestion]
