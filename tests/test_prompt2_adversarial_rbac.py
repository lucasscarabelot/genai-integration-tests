"""
Casos de Teste de Integração gerados a partir do:
PROMPT TIPO 2: Adversarial, Casos Limite e Matriz de Permissões RBAC (Adversarial & RBAC Security Prompt)

Objetivo do Prompt 2:
- Testar falhas de segurança e integridade entre módulos (Auth <-> Resource Access <-> Audit)
- Tentar escalonamento de privilégios (Privilege Escalation)
- Validar segregação de dados confidenciais por papel (Data Leakage Prevention)
- Forçar anomalias de token: assinatura forjada, expiração, token de refresh usado como access
- Rotação de refresh token (bloqueio de replay attack) e usuário desativado
"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from app.auth import SECRET_KEY, ALGORITHM
from app.database import db

def test_rbac_privilege_escalation_viewer_cannot_create_document(client, viewer_headers):
    """
    Tenta criar documento usando credenciais de VIEWER.
    Deve ser terminantemente bloqueado com HTTP 403 Forbidden.
    """
    payload = {
        "title": "Tentativa de Post não Autorizado",
        "content": "Conteúdo injetado por Viewer sem permissão",
        "is_confidential": False
    }
    response = client.post("/api/v1/documents", json=payload, headers=viewer_headers)
    assert response.status_code == 403
    assert "Permissão negada" in response.json()["detail"]

def test_rbac_privilege_escalation_editor_cannot_delete_document(client, editor_headers):
    """
    Tenta deletar um documento usando credenciais de EDITOR.
    Apenas ADMIN pode deletar. Deve retornar HTTP 403 Forbidden.
    """
    response = client.delete("/api/v1/documents/1", headers=editor_headers)
    assert response.status_code == 403
    assert "Permissão negada" in response.json()["detail"]

def test_rbac_data_segregation_confidential_documents_filtered_for_viewer(client, viewer_headers, admin_headers):
    """
    Garante que documentos com flag `is_confidential=True` nunca vazem para VIEWERS,
    mas estejam disponíveis para ADMINS.
    """
    # 1. Requisição como Viewer
    viewer_res = client.get("/api/v1/documents", headers=viewer_headers)
    assert viewer_res.status_code == 200
    viewer_docs = viewer_res.json()
    assert all(doc["is_confidential"] is False for doc in viewer_docs)

    # 2. Requisição como Admin
    admin_res = client.get("/api/v1/documents", headers=admin_headers)
    assert admin_res.status_code == 200
    admin_docs = admin_res.json()
    assert any(doc["is_confidential"] is True for doc in admin_docs)

def test_forged_signature_token_rejected(client):
    """
    Gera um token com assinatura utilizando chave secreta falsa (hacker attempt).
    Deve retornar 401 Unauthorized por assinatura inválida.
    """
    now = datetime.now(timezone.utc)
    fake_payload = {
        "sub": "admin_user",
        "role": "admin",
        "type": "access",
        "exp": now + timedelta(hours=1)
    }
    fake_secret = "chave-falsa-do-atacante-com-mais-de-32-bytes-para-teste"
    fake_token = jwt.encode(fake_payload, fake_secret, algorithm="HS256")
    headers = {"Authorization": f"Bearer {fake_token}"}

    response = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert response.status_code == 401
    assert "Token inválido ou corrompido" in response.json()["detail"]

def test_expired_token_rejected(client):
    """
    Testa comportamento com token cujo timestamp `exp` já passou.
    Deve retornar 401 Unauthorized explicitly.
    """
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "admin_user",
        "role": "admin",
        "type": "access",
        "exp": now - timedelta(minutes=5)
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Token expirado" in response.json()["detail"]

def test_refresh_token_used_as_access_token_rejected(client, admin_tokens):
    """
    Boundary case: o cliente tenta usar o `refresh_token` no header de autorização
    de uma rota protegida de API. Deve ser rejeitado por tipo inadequado.
    """
    refresh_token = admin_tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {refresh_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Tipo de token inválido" in response.json()["detail"]

def test_token_rotation_prevents_replay_attack(client, admin_tokens):
    """
    Testa rotação de Refresh Token:
    1. Usa o refresh_token para obter um novo par
    2. Tenta reusar o refresh_token antigo (replay attack)
    3. Deve falhar com 401 Unauthorized por ter sido revogado na primeira rotação
    """
    old_refresh_token = admin_tokens["refresh_token"]

    # Primeiro refresh: bem sucedido
    first_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first_res.status_code == 200

    # Segundo refresh usando o mesmo token antigo: deve ser bloqueado
    second_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert second_res.status_code == 401
    assert "Token revogado" in second_res.json()["detail"]

def test_inactive_user_cannot_login_and_cannot_access_routes(client):
    """
    Usuário cadastrado porém marcado com is_active=False:
    1. Tentativa de login é barrada com 403 Forbidden
    2. Se possuir token pré-existente, o middleware/dependência rejeita com 403 Forbidden
    """
    # 1. Login bloqueado
    login_res = client.post("/api/v1/auth/login", json={
        "username": "inactive_user",
        "password": "Inactive@123456"
    })
    assert login_res.status_code == 403
    assert "Conta inativa" in login_res.json()["detail"]

    # 2. Token pré-existente
    now = datetime.now(timezone.utc)
    active_token_payload = {
        "sub": "inactive_user",
        "role": "viewer",
        "type": "access",
        "exp": now + timedelta(hours=1)
    }
    token = jwt.encode(active_token_payload, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 403
    assert "Usuário inativo" in me_res.json()["detail"]

def test_audit_logs_record_forbidden_and_authorized_actions(client, viewer_headers, admin_headers):
    """
    Valida a integração transversal com o serviço de Auditoria:
    Todas as ações (tanto autorizadas quanto barradas) devem gerar entradas no log.
    """
    # Limpa logs do teste
    db.audit_logs.clear()

    # Viewer tenta ação proibida (403)
    client.post("/api/v1/documents", json={"title": "Hack", "content": "Teste"}, headers=viewer_headers)

    # Admin faz consulta de auditoria (200)
    admin_res = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert admin_res.status_code == 200
    logs = admin_res.json()

    # Verifica se a tentativa proibida do viewer foi registrada
    forbidden_logs = [l for l in logs if l["username"] == "viewer_user" and l["status_code"] == 403]
    assert len(forbidden_logs) >= 1
