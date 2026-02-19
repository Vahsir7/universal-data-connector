import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.models.assistant import LLMProvider
from app.services.db import get_db_service


class LlmApiKeyService:
    def __init__(self) -> None:
        self._db = get_db_service()
        self._bootstrap_env_keys()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _provider_env_key(provider: LLMProvider) -> str:
        if provider == LLMProvider.openai:
            return (settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else "").strip()
        if provider == LLMProvider.anthropic:
            return (settings.ANTHROPIC_API_KEY.get_secret_value() if settings.ANTHROPIC_API_KEY else "").strip()
        if provider == LLMProvider.gemini:
            return (settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else "").strip()
        return ""

    @staticmethod
    def _provider_default_model(provider: LLMProvider) -> str:
        if provider == LLMProvider.openai:
            return settings.OPENAI_MODEL
        if provider == LLMProvider.anthropic:
            return settings.ANTHROPIC_MODEL
        if provider == LLMProvider.gemini:
            return settings.GEMINI_MODEL
        return ""

    @staticmethod
    def _mask_key(key_value: str) -> str:
        cleaned = (key_value or "").strip()
        if not cleaned:
            return ""
        if len(cleaned) <= 4:
            return "****"
        return f"{'*' * max(4, len(cleaned) - 4)}{cleaned[-4:]}"

    def _bootstrap_env_keys(self) -> None:
        for provider in LLMProvider:
            key_value = self._provider_env_key(provider)
            if not key_value:
                continue

            key_hash = self._hash_key(key_value)
            existing = self._db.fetchone(
                "SELECT key_id FROM llm_provider_keys WHERE provider = ? AND source = 'env' AND key_hash = ?",
                (provider.value, key_hash),
            )
            if existing is not None:
                continue

            self._db.execute(
                """
                INSERT INTO llm_provider_keys (key_id, name, provider, model, key_hash, key_value, source, created_at, revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    str(uuid.uuid4()),
                    f"default-{provider.value}",
                    provider.value,
                    self._provider_default_model(provider),
                    key_hash,
                    key_value,
                    "env",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_keys(self, provider: Optional[LLMProvider] = None) -> List[Dict[str, str | bool]]:
        params: Tuple[str, ...] = ()
        where = ""
        if provider is not None:
            where = "WHERE provider = ?"
            params = (provider.value,)

        rows = self._db.fetchall(
            f"""
            SELECT key_id, name, provider, model, source, revoked, created_at, last_used_at, key_value
            FROM llm_provider_keys
            {where}
            ORDER BY created_at DESC
            """,
            params,
        )

        return [
            {
                "key_id": str(row["key_id"]),
                "name": str(row["name"]),
                "provider": str(row["provider"]),
                "model": str(row["model"] or self._provider_default_model(LLMProvider(str(row["provider"])))),
                "api_key_masked": self._mask_key(str(row["key_value"] or "")),
                "source": str(row["source"]),
                "revoked": bool(row["revoked"]),
                "created_at": str(row["created_at"]),
                "last_used_at": str(row["last_used_at"] or ""),
            }
            for row in rows
        ]

    def create_key(self, provider: LLMProvider, name: str, key_value: str, model: Optional[str] = None) -> Dict[str, str]:
        key_id = str(uuid.uuid4())
        model_name = (model or self._provider_default_model(provider)).strip() or self._provider_default_model(provider)
        self._db.execute(
            """
            INSERT INTO llm_provider_keys (key_id, name, provider, model, key_hash, key_value, source, created_at, revoked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                key_id,
                name,
                provider.value,
                model_name,
                self._hash_key(key_value),
                key_value,
                "manual",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return {"key_id": key_id, "name": name, "provider": provider.value, "model": model_name}

    def revoke_key(self, key_id: str) -> bool:
        changed = self._db.execute("UPDATE llm_provider_keys SET revoked = 1 WHERE key_id = ?", (key_id,))
        return changed > 0

    def resolve_key(self, provider: LLMProvider, api_key_id: Optional[str], manual_api_key: Optional[str]) -> str:
        if manual_api_key and manual_api_key.strip():
            return manual_api_key.strip()

        if api_key_id and api_key_id.strip():
            row = self._db.fetchone(
                """
                SELECT key_id, key_value FROM llm_provider_keys
                WHERE key_id = ? AND provider = ? AND revoked = 0
                LIMIT 1
                """,
                (api_key_id.strip(), provider.value),
            )
            if row is not None:
                self._db.execute(
                    "UPDATE llm_provider_keys SET last_used_at = ? WHERE key_id = ?",
                    (datetime.now(timezone.utc).isoformat(), str(row["key_id"])),
                )
                return str(row["key_value"])

        env_key = self._provider_env_key(provider)
        if env_key:
            return env_key

        raise ValueError(f"No API key available for provider '{provider.value}'")


llm_api_key_service = LlmApiKeyService()
