from .classifier import VERSION_MODELE
from .schemas import (
    AssigneeSuggestion,
    SuggestAssigneeRequest,
    SuggestAssigneeResponse,
)


def suggerer_responsables(req: SuggestAssigneeRequest) -> SuggestAssigneeResponse:
    tache = req.tache
    candidats = [c for c in req.candidats if c.actif]

    if not candidats:
        return SuggestAssigneeResponse(version_modele=VERSION_MODELE, suggestions=[])

    # Les tâches urgentes déjà en cours pèsent plus lourd dans la charge effective
    def charge(c) -> int:
        return c.charge_en_cours + c.charge_urgente

    charge_max = max(charge(c) for c in candidats)

    # Si la tâche est urgente, la disponibilité compte davantage que le département
    if tache.priorite == "urgent":
        poids_dept, poids_charge = 0.4, 0.6
    else:
        poids_dept, poids_charge = 0.5, 0.5

    resultats: list[tuple[float, int, int, AssigneeSuggestion]] = []
    for c in candidats:
        if tache.departement_id is None:
            score_dept, texte_dept = 0.5, None  # neutre : n'avantage personne
        elif c.departement_id == tache.departement_id:
            score_dept, texte_dept = 1.0, "même département"
        else:
            score_dept, texte_dept = 0.0, "autre département"

        score_charge = 1.0 if charge_max == 0 else 1 - charge(c) / charge_max
        score = round(poids_dept * score_dept + poids_charge * score_charge, 4)

        elements = [texte_dept] if texte_dept else []
        elements.append(
            f"{c.charge_en_cours} tâche(s) en cours ou en attente"
            + (f", dont {c.charge_urgente} urgente(s)" if c.charge_urgente else "")
        )
        resultats.append(
            (
                score,
                charge(c),
                c.id,
                AssigneeSuggestion(
                    utilisateur_id=c.id,
                    nom=c.nom,
                    score=score,
                    raison="; ".join(elements),
                ),
            )
        )

    # Meilleur score d'abord, puis charge la plus faible, puis id (ordre stable)
    resultats.sort(key=lambda r: (-r[0], r[1], r[2]))
    return SuggestAssigneeResponse(
        version_modele=VERSION_MODELE,
        suggestions=[r[3] for r in resultats[: req.limite]],
    )
