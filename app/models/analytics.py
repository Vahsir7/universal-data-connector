"""Pydantic models for analytics / metrics records."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsMetric(BaseModel):
    """Single analytics metric data point."""

    model_config = ConfigDict(extra="allow")

    metric: str = Field(..., min_length=1, description="Metric name (e.g. daily_active_users)")
    date: str = Field(..., description="ISO-8601 date for this data point")
    value: Any = Field(..., description="Metric value (numeric or structured)")
