"""Database validation schemas."""

from pydantic import BaseModel, Field


class TableValidationResult(BaseModel):
    """Result of database table validation."""

    all_exist: bool = Field(..., description="Whether all core tables exist")
    missing_tables: list[str] = Field(
        default_factory=list, description="List of missing core tables"
    )
    optional_missing: list[str] = Field(
        default_factory=list, description="List of missing optional tables"
    )


class DatabaseMigrationResult(BaseModel):
    """Result of migration application."""

    success: bool = Field(..., description="Whether all migrations succeeded")
    applied_migrations: list[str] = Field(
        default_factory=list, description="List of successfully applied migrations"
    )
    failed_migrations: list[str] = Field(
        default_factory=list, description="List of failed migrations"
    )
