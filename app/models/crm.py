"""Pydantic models for CRM / customer records."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Customer(BaseModel):
    """Single CRM customer record."""

    model_config = ConfigDict(extra="allow")

    customer_id: int = Field(..., ge=1, description="Unique customer identifier")
    name: str = Field(..., min_length=1, description="Customer display name")
    email: str = Field(..., description="Contact email address")
    created_at: Optional[str] = Field(default=None, description="ISO-8601 creation timestamp")
    status: Optional[str] = Field(default=None, description="Account status (active / inactive)")
