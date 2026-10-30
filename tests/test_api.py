import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEPARTEMENTS = [
    {"id": 1, "nom": "Finance", "description": "Comptabilité, budget, factures, paiements"},
    {"id": 2, "nom": "Informatique", "description": "Réseau, serveurs, logiciels, maintenance"},
    {"id": 3, "nom": "Ressources humaines", "description": "Recrutement, congés, paie, formation"},
]


@pytest.fixture(autouse=True)
def sans_cle(monkeypatch):
    monkeypatch.delenv("AI_SERVICE_KEY", raising=False)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["statut"] == "ok"


def test_priorite_urgente_depuis_le_texte():
    r = client.post("/classify", json={
        "tache": {"titre": "Panne serveur : correction URGENTE", "description": "Bloquant pour tous"},
    })
    assert r.status_code == 200
    assert r.json()["priorite"]["valeur"] == "urgent"


def test_priorite_normale_par_defaut():
    r = client.post("/classify", json={"tache": {"titre": "Ranger les archives"}})
    assert r.json()["priorite"]["valeur"] == "normal"


def test_echeance_proche_releve_la_priorite():
    r = client.post("/classify", json={
        "tache": {"titre": "Ranger les archives", "date_echeance": "2026-10-14"},
        "date_reference": "2026-10-12",
    })
    assert r.json()["priorite"]["valeur"] == "important"


def test_echeance_depassee_est_urgente():
    r = client.post("/classify", json={
        "tache": {"titre": "Ranger les archives", "date_echeance": "2026-10-10"},
        "date_reference": "2026-10-12",
    })
    assert r.json()["priorite"]["valeur"] == "urgent"


def test_departement_suggere():
    r = client.post("/classify", json={
        "tache": {"titre": "Régler les factures fournisseurs", "description": "Paiements du mois"},
        "departements": DEPARTEMENTS,
    })
    assert r.json()["departement"]["departement_id"] == 1


def test_departement_inconnu():
    r = client.post("/classify", json={
        "tache": {"titre": "Organiser le pot de fin d'année"},
        "departements": DEPARTEMENTS,
    })
    assert r.json()["departement"]["departement_id"] is None


def test_assignation_prefere_meme_departement_et_faible_charge():
    r = client.post("/suggest-assignee", json={
        "tache": {"titre": "x", "departement_id": 1, "priorite": "normal"},
        "candidats": [
            {"id": 10, "nom": "A", "departement_id": 1, "charge_en_cours": 5},
            {"id": 11, "nom": "B", "departement_id": 1, "charge_en_cours": 1},
            {"id": 12, "nom": "C", "departement_id": 2, "charge_en_cours": 0},
        ],
    })
    ids = [s["utilisateur_id"] for s in r.json()["suggestions"]]
    assert ids[0] == 11
    assert len(ids) == 3


def test_assignation_exclut_les_inactifs():
    r = client.post("/suggest-assignee", json={
        "tache": {"titre": "x"},
        "candidats": [
            {"id": 1, "nom": "Inactif", "charge_en_cours": 0, "actif": False},
            {"id": 2, "nom": "Actif", "charge_en_cours": 4},
        ],
    })
    ids = [s["utilisateur_id"] for s in r.json()["suggestions"]]
    assert ids == [2]


def test_assignation_tous_inactifs():
    r = client.post("/suggest-assignee", json={
        "tache": {"titre": "x"},
        "candidats": [{"id": 1, "nom": "Inactif", "actif": False}],
    })
    assert r.json()["suggestions"] == []


def test_tache_urgente_privilegie_la_disponibilite():
    r = client.post("/suggest-assignee", json={
        "tache": {"titre": "x", "departement_id": 1, "priorite": "urgent"},
        "candidats": [
            {"id": 1, "nom": "Surchargé du département", "departement_id": 1, "charge_en_cours": 8, "charge_urgente": 3},
            {"id": 2, "nom": "Libre ailleurs", "departement_id": 2, "charge_en_cours": 0},
        ],
    })
    assert r.json()["suggestions"][0]["utilisateur_id"] == 2


def test_cle_api_obligatoire_quand_definie(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_KEY", "secret")
    corps = {"tache": {"titre": "x"}}
    assert client.post("/classify", json=corps).status_code == 401
    assert client.post("/classify", json=corps, headers={"X-API-Key": "faux"}).status_code == 401
    assert client.post("/classify", json=corps, headers={"X-API-Key": "secret"}).status_code == 200


def test_titre_vide_refuse():
    assert client.post("/classify", json={"tache": {"titre": ""}}).status_code == 422
