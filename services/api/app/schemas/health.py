from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for service health check response."""

    status: str = Field(..., description="Overall health status: 'healthy' or 'degraded'")
    environment: str = Field(
        ..., description="Active environment name (development, staging, production)"
    )
    version: str = Field(..., description="Application version")
    database: str | None = Field(default="pending", description="Database connectivity status")
