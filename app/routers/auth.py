from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.auth import api_key_service, require_admin_key


router = APIRouter(prefix="/auth", tags=["Auth"], dependencies=[Depends(require_admin_key)])


class CreateApiKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)


class ApiKeyCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    name: str
    api_key: str


class ApiKeyInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    name: str
    created_at: str
    revoked: bool
    source: str
    last_used_at: str


class ApiKeyOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    name: str
    api_key: str
    revoked: bool
    source: str


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
def create_api_key(payload: CreateApiKeyRequest) -> ApiKeyCreateResponse:
    created = api_key_service.create_api_key(name=payload.name)
    return ApiKeyCreateResponse.model_validate(created)


@router.get("/api-keys", response_model=List[ApiKeyInfo])
def list_api_keys() -> List[ApiKeyInfo]:
    records = api_key_service.list_api_keys()
    return [ApiKeyInfo.model_validate(item) for item in records]


@router.get("/api-keys/options", response_model=List[ApiKeyOption])
def list_api_key_options() -> List[ApiKeyOption]:
    records = api_key_service.list_api_key_options()
    return [ApiKeyOption.model_validate(item) for item in records]


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: str):
    ok = api_key_service.revoke_api_key(key_id=key_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "API_KEY_NOT_FOUND",
                "message": f"No API key found for id '{key_id}'",
            },
        )
    return {"status": "revoked", "key_id": key_id}
