# tests/test_routes.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../api')))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_route_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_route_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "cpu_percent" in response.json()

def test_post_server_auth_protection_denied():
    """Un post sans en-tête d'authentification doit lever un code d'erreur 403."""
    payload = {"name": "test-env", "host": "localhost", "port": 9000}
    response = client.post("/servers", json=payload)
    assert response.status_code == 403

def test_server_lifecycle_nominal_path():
    """Validation de bout-en-bout du cycle d'un serveur (Enregistrement, Lecture, Erreur 404)."""
    headers = {"X-API-Key": "demo-key"}
    payload = {"name": "api-integration-test", "host": "httpbin.org", "port": 80}
    
    # 1. Création avec succès
    post_res = client.post("/servers", json=payload, headers=headers)
    assert post_res.status_code == 201
    server_id = post_res.json()["id"]
    
    # 2. Présence dans la liste globale publique
    get_res = client.get("/servers")
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1
    
    # 3. Test de levée 404 sur ID inexistant
    get_fail = client.get("/servers/99999")
    assert get_fail.status_code == 404
