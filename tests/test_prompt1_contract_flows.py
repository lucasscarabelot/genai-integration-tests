"""
Casos de Teste de Integração gerados a partir do:
PROMPT TIPO 1: Baseado em Especificação de Contrato e Fluxo de Estado (Specification & Contract-Driven Prompt)

Objetivo do Prompt 1:
- Validar conformidade de contrato de API (OpenAPI/Pydantic schemas)
- Cobrir ciclo de vida padrão de autenticação: Login -> Consumo de API -> Refresh de Token -> Logout
- Verificar respostas HTTP adequadas (200, 201, 400, 401, 422)
"""

import pytest

def test_health_check_contract(client):
    """Garante que o endpoint de integridade responde conforme o contrato mínimo."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_login_flow_positive(client):
    """
    Fluxo positivo de autenticação:
    1. Envia credenciais válidas
    2. Recebe access_token e refresh_token com contrato esperado
    3. Valida tipos e expiração
    """
    payload = {
        "username": "editor_user",
        "password": "Editor@123456"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 15 * 60

def test_login_invalid_credentials(client):
    """Validação de contrato de erro ao submeter senha incorreta (HTTP 401)."""
    payload = {
        "username": "editor_user",
        "password": "SenhaCompletamenteErrada"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Credenciais inválidas" in response.json()["detail"]

def test_login_schema_validation_error(client):
    """Validação de schema Pydantic: username menor que o mínimo exigido (HTTP 422)."""
    payload = {
        "username": "ab", # min 3
        "password": "123" # min 6
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert len(errors) >= 1

def test_protected_route_without_token(client):
    """Verifica que requisição sem header Authorization retorna 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Header de autorização não fornecido" in response.json()["detail"]

def test_full_authentication_lifecycle_flow(client):
    """
    Fluxo completo de integração:
    Login -> Consumir /me -> Refresh Token -> Consumir /me novamente -> Logout -> Tentar /me (401)
    """
    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin_user",
        "password": "Admin@123456"
    })
    assert login_res.status_code == 200
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Acesso à rota protegida
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin_user"
    assert me_res.json()["role"] == "admin"

    # 3. Renovação de token (Refresh)
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    new_access_token = new_tokens["access_token"]
    assert new_access_token != access_token

    # 4. Acesso com novo token
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    me_res_2 = client.get("/api/v1/auth/me", headers=new_headers)
    assert me_res_2.status_code == 200

    # 5. Logout
    logout_res = client.post("/api/v1/auth/logout", headers=new_headers)
    assert logout_res.status_code == 200

    # 6. Tentativa de reuso do token revogado
    me_res_revoked = client.get("/api/v1/auth/me", headers=new_headers)
    assert me_res_revoked.status_code == 401
    assert "Token revogado" in me_res_revoked.json()["detail"]
