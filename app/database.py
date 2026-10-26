import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models import UserRole

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class MockDatabase:
    def __init__(self):
        self.reset()

    def reset(self):
        now = datetime.now(timezone.utc)
        self.users: Dict[str, dict] = {
            "admin_user": {
                "id": 1,
                "username": "admin_user",
                "email": "admin@empresa.com",
                "password_hash": hash_password("Admin@123456"),
                "role": UserRole.ADMIN,
                "is_active": True,
            },
            "editor_user": {
                "id": 2,
                "username": "editor_user",
                "email": "editor@empresa.com",
                "password_hash": hash_password("Editor@123456"),
                "role": UserRole.EDITOR,
                "is_active": True,
            },
            "viewer_user": {
                "id": 3,
                "username": "viewer_user",
                "email": "viewer@empresa.com",
                "password_hash": hash_password("Viewer@123456"),
                "role": UserRole.VIEWER,
                "is_active": True,
            },
            "inactive_user": {
                "id": 4,
                "username": "inactive_user",
                "email": "inactive@empresa.com",
                "password_hash": hash_password("Inactive@123456"),
                "role": UserRole.VIEWER,
                "is_active": False,
            },
        }

        self.documents: Dict[int, dict] = {
            1: {
                "id": 1,
                "title": "Documento Geral",
                "content": "Conteúdo público para todos os colaboradores.",
                "is_confidential": False,
                "owner_id": 2,
                "created_at": now,
            },
            2: {
                "id": 2,
                "title": "Relatório Estratégico Financeiro",
                "content": "Conteúdo altamente confidencial da diretoria.",
                "is_confidential": True,
                "owner_id": 1,
                "created_at": now,
            },
        }

        self.revoked_tokens: set = set()
        self.audit_logs: List[dict] = []
        self._doc_seq = 2
        self._log_seq = 0

    def add_audit_log(self, username: str, endpoint: str, method: str, status_code: int):
        self._log_seq += 1
        self.audit_logs.append({
            "id": self._log_seq,
            "timestamp": datetime.now(timezone.utc),
            "username": username,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
        })

db = MockDatabase()
