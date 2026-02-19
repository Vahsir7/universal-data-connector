"""Pydantic models for support ticket records."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SupportTicket(BaseModel):
    """Single support ticket record."""

    model_config = ConfigDict(extra="allow")

    ticket_id: int = Field(..., ge=1, description="Unique ticket identifier")
    customer_id: int = Field(..., ge=1, description="Owning customer identifier")
    subject: str = Field(..., min_length=1, description="Ticket subject line")
    priority: Optional[str] = Field(default=None, description="Priority level (low / medium / high)")
    created_at: Optional[str] = Field(default=None, description="ISO-8601 creation timestamp")
    status: Optional[str] = Field(default=None, description="Ticket status (open / closed)")
