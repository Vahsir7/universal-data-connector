import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import Header, HTTPException

from app.config import settings
from app.services.db import get_db_service


class ApiKeyService:
    def __init__(self) -> None:
        self._db = get_db_service()
        self._bootstrap_env_keys()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _bootstrap_env_keys(self) -> None:
        raw = settings.DEFAULT_CLIENT_API_KEYS.strip()
        if not raw:
            return

        keys = [key.strip() for key in raw.split(",") if key.strip()]
        for index, key_value in enumerate(keys, start=1):
            key_hash = self._hash_key(key_value)
            existing = self._db.fetchone("SELECT key_id FROM api_keys WHERE key_hash = ?", (key_hash,))
            if existing is not None:
                continue

            key_id = str(uuid.uuid4())
            self._db.execute(
                """
                INSERT INTO api_keys (key_id, name, key_hash, key_value, source, created_at, revoked)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    key_id,
                    f"env-default-{index}",
                    key_hash,
                    key_value,
                    "env",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def create_api_key(self, name: str) -> Dict[str, str]:
        key_id = str(uuid.uuid4())
        plaintext_key = f"udc_{secrets.token_urlsafe(24)}"
        created_at = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            """
            INSERT INTO api_keys (key_id, name, key_hash, key_value, source, created_at, revoked)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (key_id, name, self._hash_key(plaintext_key), plaintext_key, "generated", created_at),
        )
        return {"key_id": key_id, "api_key": plaintext_key, "name": name}

    def list_api_keys(self) -> List[Dict[str, str | bool]]:
        rows = self._db.fetchall(
            """
            SELECT key_id, name, created_at, revoked, source, last_used_at
            FROM api_keys
            ORDER BY created_at DESC
            """
        )
        return [
            {
                "key_id": str(row["key_id"]),
                "name": str(row["name"]),
                "created_at": str(row["created_at"]),
                "revoked": bool(row["revoked"]),
                "source": str(row["source"]),
                "last_used_at": str(row["last_used_at"] or ""),
            }
            for row in rows
        ]

    def list_api_key_options(self) -> List[Dict[str, str | bool]]:
        rows = self._db.fetchall(
            """
            SELECT key_id, name, key_value, revoked, source
            FROM api_keys
            ORDER BY created_at DESC
            """
        )
        return [
            {
                "key_id": str(row["key_id"]),
                "name": str(row["name"]),
                "api_key": str(row["key_value"] or ""),
                "revoked": bool(row["revoked"]),
                "source": str(row["source"]),
            }
            for row in rows
        ]

    def revoke_api_key(self, key_id: str) -> bool:
        changed = self._db.execute("UPDATE api_keys SET revoked = 1 WHERE key_id = ?", (key_id,))
        return changed > 0

    def reset_for_tests(self) -> None:
        self._db.execute("DELETE FROM api_keys")
        self._bootstrap_env_keys()

    def validate_api_key(self, key: str) -> bool:
        key_hash = self._hash_key(key)
        row = self._db.fetchone(
            """
            SELECT key_id FROM api_keys
            WHERE key_hash = ? AND revoked = 0
            LIMIT 1
            """,
            (key_hash,),
        )
        if row is None:
            return False

        self._db.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
            (datetime.now(timezone.utc).isoformat(), str(row["key_id"])),
        )
        return True


api_key_service = ApiKeyService()


def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    if not settings.AUTH_ENABLED:
        return
    if x_api_key is None or not api_key_service.validate_api_key(x_api_key):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_INVALID_API_KEY",
                "message": "Valid API key required in X-API-Key header",
            },
        )


def require_admin_key(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")) -> None:
    admin_secret = settings.ADMIN_API_KEY.get_secret_value() if settings.ADMIN_API_KEY else ""
    if x_admin_key is None or x_admin_key != admin_secret:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTH_INVALID_ADMIN_KEY",
                "message": "Valid admin key required in X-Admin-Key header",
            },
        )
