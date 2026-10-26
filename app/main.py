from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from app.models import (
    UserRole,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    DocumentCreate,
    DocumentResponse,
    AuditLogEntry,
)
from app.database import db, hash_password
from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_roles,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    security,
)
from fastapi.security import HTTPAuthorizationCredentials

app = FastAPI(
    title="Auth & RBAC Integration API",
    description="API para testes de integração com foco em autenticação JWT, RBAC e resiliência de rotas",
    version="1.0.0",
)

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1") and request.url.path != "/api/v1/health":
        auth_header = request.headers.get("authorization", "")
        username = "anonymous"
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = decode_token(token)
                username = payload.get("sub", "unknown")
            except Exception:
                username = "invalid_token"
        db.add_audit_log(
            username=username,
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
        )
    return response

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(request: LoginRequest):
    user = db.users.get(request.username)
    if not user or user["password_hash"] != hash_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas: usuário ou senha incorretos",
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa. Contate o administrador.",
        )

    access_token = create_access_token({"sub": user["username"], "role": user["role"].value})
    refresh_token = create_refresh_token({"sub": user["username"]})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

@app.post("/api/v1/auth/refresh", response_model=TokenResponse, tags=["Auth"])
def refresh_token(request: RefreshTokenRequest):
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token fornecido não é um refresh token válido",
        )

    username = payload.get("sub")
    user = db.users.get(username)
    if not user or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado ao refresh token inválido ou inativo",
        )

    new_access_token = create_access_token({"sub": user["username"], "role": user["role"].value})
    new_refresh_token = create_refresh_token({"sub": user["username"]})

    db.revoked_tokens.add(request.refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

@app.post("/api/v1/auth/logout", tags=["Auth"])
def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    token = credentials.credentials
    db.revoked_tokens.add(token)
    return {"message": "Sessão encerrada com sucesso e token revogado"}

@app.get("/api/v1/auth/me", response_model=UserResponse, tags=["Auth"])
def get_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        is_active=current_user["is_active"],
    )

@app.get("/api/v1/documents", response_model=List[DocumentResponse], tags=["Documents"])
def list_documents(current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    docs = list(db.documents.values())
    if user_role == UserRole.VIEWER:
        return [doc for doc in docs if not doc["is_confidential"]]
    return docs

@app.post("/api/v1/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, tags=["Documents"])
def create_document(
    doc: DocumentCreate,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.EDITOR]))
):
    db._doc_seq += 1
    new_doc = {
        "id": db._doc_seq,
        "title": doc.title,
        "content": doc.content,
        "is_confidential": doc.is_confidential,
        "owner_id": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    db.documents[new_doc["id"]] = new_doc
    return DocumentResponse(**new_doc)

@app.delete("/api/v1/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Documents"])
def delete_document(
    doc_id: int,
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    if doc_id not in db.documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado")
    del db.documents[doc_id]
    return None

@app.get("/api/v1/admin/audit-logs", response_model=List[AuditLogEntry], tags=["Admin"])
def get_audit_logs(current_user: dict = Depends(require_roles([UserRole.ADMIN]))):
    return [AuditLogEntry(**log) for log in db.audit_logs]
