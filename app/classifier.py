from datetime import date
from typing import Optional

from .schemas import (
    ClassifyRequest,
    ClassifyResponse,
    Departement,
    DepartementSuggestion,
    PrioriteSuggestion,
)
from .text_utils import normalize, tokenize

VERSION_MODELE = "regles_v1"

# Listes volontairement simples et modifiables : à ajuster avec les retours du terrain.
TERMES_URGENT = [
    "urgent", "urgence", "immediat", "asap", "critique", "bloquant",
    "sans delai", "au plus vite", "des que possible", "aujourd'hui",
]
TERMES_IMPORTANT = [
    "important", "prioritaire", "essentiel", "indispensable", "audit",
    "conformite", "reglementaire", "client",
]

ORDRE = {"normal": 0, "important": 1, "urgent": 2}


def _termes_trouves(texte: str, termes: list[str]) -> list[str]:
    return [t for t in termes if t in texte]


def suggerer_priorite(
    titre: str,
    description: Optional[str],
    date_echeance: Optional[date],
    aujourd_hui: date,
) -> PrioriteSuggestion:
    texte = normalize(f"{titre} {description or ''}")

    valeur, confiance = "normal", 0.5
    raisons: list[str] = []

    urgents = _termes_trouves(texte, TERMES_URGENT)
    importants = _termes_trouves(texte, TERMES_IMPORTANT)
    if urgents:
        valeur, confiance = "urgent", 0.75
        raisons.append(f"termes d'urgence détectés ({', '.join(urgents)})")
    elif importants:
        valeur, confiance = "important", 0.6
        raisons.append(f"termes d'importance détectés ({', '.join(importants)})")

    if date_echeance is not None:
        jours = (date_echeance - aujourd_hui).days
        if jours <= 1:
            cible, conf_e = "urgent", 0.9
            raisons.append("échéance dépassée" if jours < 0 else "échéance dans 24 h au plus")
        elif jours <= 7:
            cible, conf_e = "important", 0.8
            raisons.append(f"échéance dans {jours} jours")
        else:
            cible, conf_e = "normal", 0.5
        if ORDRE[cible] > ORDRE[valeur]:
            valeur, confiance = cible, conf_e
        elif ORDRE[cible] == ORDRE[valeur]:
            confiance = max(confiance, conf_e)

    if not raisons:
        raisons.append("aucun signal d'urgence détecté")

    return PrioriteSuggestion(
        valeur=valeur, confiance=round(confiance, 2), raison="; ".join(raisons)
    )


def suggerer_departement(
    titre: str, description: Optional[str], departements: list[Departement]
) -> Optional[DepartementSuggestion]:
    if not departements:
        return None

    mots_tache = tokenize(f"{titre} {description or ''}")

    meilleur: Optional[Departement] = None
    meilleur_score = 0.0
    meilleurs_mots: set[str] = set()

    for dep in departements:
        poids: dict[str, int] = {}
        for mot in tokenize(dep.description):
            poids[mot] = 1
        for mot in tokenize(dep.nom):  # le nom compte double
            poids[mot] = 2
        total = sum(poids.values())
        if total == 0:
            continue
        communs = mots_tache & poids.keys()
        score = sum(poids[m] for m in communs) / total
        if score > meilleur_score:
            meilleur, meilleur_score, meilleurs_mots = dep, score, communs

    if meilleur is None or meilleur_score == 0:
        return DepartementSuggestion(
            departement_id=None,
            confiance=0.0,
            raison="aucun mot du titre ou de la description ne correspond à un département",
        )

    return DepartementSuggestion(
        departement_id=meilleur.id,
        confiance=round(min(0.9, meilleur_score * 1.5), 2),
        raison=f"mots en commun avec « {meilleur.nom} » ({', '.join(sorted(meilleurs_mots))})",
    )


def classifier(req: ClassifyRequest) -> ClassifyResponse:
    aujourd_hui = req.date_reference or date.today()
    t = req.tache
    return ClassifyResponse(
        version_modele=VERSION_MODELE,
        priorite=suggerer_priorite(t.titre, t.description, t.date_echeance, aujourd_hui),
        departement=suggerer_departement(t.titre, t.description, req.departements),
    )
