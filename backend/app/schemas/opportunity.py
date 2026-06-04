from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpportunityBase(BaseModel):
    seace_id: int
    entity_name: str | None = None
    process_type: str | None = None
    nomenclature: str | None = None
    object_type: str | None = None
    item_description: str | None = None
    cubso_code: str | None = None
    cubso_description: str | None = None
    process_summary: str | None = None
    publish_date: datetime | None = None
    end_date: datetime | None = None
    keyword: str
    raw_json: dict[str, Any]


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityRead(OpportunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class OpportunityListResponse(BaseModel):
    items: list[OpportunityRead]
    total: int
    limit: int
    offset: int


class CrawlRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=255)
    cod_objeto: int = 0
    cod_departamento: int = 0
    cod_tipo_proceso: int = 0


class BulkCrawlRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=100)
    cod_objeto: int = 0
    cod_departamento: int = 0
    cod_tipo_proceso: int = 0


class CrawlResult(BaseModel):
    keyword: str
    fetched: int
    inserted: int
    duplicates: int
    failed: int
    duration_seconds: float


class BulkCrawlResult(BaseModel):
    results: list[CrawlResult]
    fetched: int
    inserted: int
    duplicates: int
    failed: int
    duration_seconds: float
