from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_app_settings, get_current_identity, get_seace_client, get_session
from app.clients.seace import SeaceClient
from app.core.config import Settings
from app.models.identity import CorporateIdentity
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import (
    BulkCrawlRequest,
    BulkCrawlResult,
    CrawlRequest,
    CrawlResult,
    OpportunityListResponse,
    OpportunityRead,
)
from app.services.crawler import CrawlerService

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    keyword: str | None = None,
    entity: str | None = None,
    process_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    identity: CorporateIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> OpportunityListResponse:
    limit = min(limit, settings.api_max_page_size)
    repository = OpportunityRepository(session)
    items, total = await repository.list_opportunities(
        keyword=keyword,
        entity=entity,
        process_type=process_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return OpportunityListResponse(
        items=[OpportunityRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(
    opportunity_id: int,
    identity: CorporateIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> OpportunityRead:
    repository = OpportunityRepository(session)
    opportunity = await repository.get_by_id(opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return OpportunityRead.model_validate(opportunity)


@router.post("/crawl", response_model=CrawlResult, status_code=status.HTTP_202_ACCEPTED)
async def crawl(
    request: CrawlRequest,
    identity: CorporateIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    seace_client: SeaceClient = Depends(get_seace_client),
) -> CrawlResult:
    service = CrawlerService(session, seace_client)
    return await service.crawl_keyword(
        keyword=request.keyword,
        cod_objeto=request.cod_objeto,
        cod_departamento=request.cod_departamento,
        cod_tipo_proceso=request.cod_tipo_proceso,
    )


@router.post("/crawl/bulk", response_model=BulkCrawlResult, status_code=status.HTTP_202_ACCEPTED)
async def crawl_bulk(
    request: BulkCrawlRequest,
    identity: CorporateIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
    seace_client: SeaceClient = Depends(get_seace_client),
) -> BulkCrawlResult:
    service = CrawlerService(session, seace_client)
    return await service.crawl_keywords(
        keywords=request.keywords,
        cod_objeto=request.cod_objeto,
        cod_departamento=request.cod_departamento,
        cod_tipo_proceso=request.cod_tipo_proceso,
    )
