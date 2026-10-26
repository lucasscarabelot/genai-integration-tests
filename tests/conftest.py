import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db

@pytest.fixture(autouse=True)
def clean_database():
    """Garante isolamento entre testes resetando o banco em memória."""
    db.reset()
    yield
    db.reset()

@pytest.fixture
def client():
    """Cliente HTTP síncrono para testes de integração de API."""
    return TestClient(app)

@pytest.fixture
def admin_tokens(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "admin_user",
        "password": "Admin@123456"
    })
    assert response.status_code == 200
    return response.json()

@pytest.fixture
def editor_tokens(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "editor_user",
        "password": "Editor@123456"
    })
    assert response.status_code == 200
    return response.json()

@pytest.fixture
def viewer_tokens(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "viewer_user",
        "password": "Viewer@123456"
    })
    assert response.status_code == 200
    return response.json()

@pytest.fixture
def admin_headers(admin_tokens):
    return {"Authorization": f"Bearer {admin_tokens['access_token']}"}

@pytest.fixture
def editor_headers(editor_tokens):
    return {"Authorization": f"Bearer {editor_tokens['access_token']}"}

@pytest.fixture
def viewer_headers(viewer_tokens):
    return {"Authorization": f"Bearer {viewer_tokens['access_token']}"}
