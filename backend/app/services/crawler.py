from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.seace import SeaceClient
from app.core.logging import get_logger
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import BulkCrawlResult, CrawlResult


class CrawlerService:
    def __init__(self, session: AsyncSession, seace_client: SeaceClient) -> None:
        self.session = session
        self.seace_client = seace_client
        self.repository = OpportunityRepository(session)
        self.logger = get_logger(__name__)

    async def crawl_keyword(
        self,
        *,
        keyword: str,
        cod_objeto: int = 0,
        cod_departamento: int = 0,
        cod_tipo_proceso: int = 0,
    ) -> CrawlResult:
        started = perf_counter()
        fetched = inserted = duplicates = failed = 0
        keyword = keyword.strip()

        try:
            opportunities = await self.seace_client.search_opportunities(
                keyword=keyword,
                cod_objeto=cod_objeto,
                cod_departamento=cod_departamento,
                cod_tipo_proceso=cod_tipo_proceso,
            )
            fetched = len(opportunities)
            inserted, duplicates = await self.repository.bulk_insert_ignore_duplicates(opportunities)
            await self.session.commit()
        except Exception as exc:
            failed = 1
            await self.session.rollback()
            self.logger.exception("crawl_keyword_failed", keyword=keyword, error=str(exc))

        duration = perf_counter() - started
        result = CrawlResult(
            keyword=keyword,
            fetched=fetched,
            inserted=inserted,
            duplicates=duplicates,
            failed=failed,
            duration_seconds=round(duration, 4),
        )
        self.logger.info("crawl_keyword_finished", **result.model_dump())
        return result

    async def crawl_keywords(
        self,
        *,
        keywords: list[str],
        cod_objeto: int = 0,
        cod_departamento: int = 0,
        cod_tipo_proceso: int = 0,
    ) -> BulkCrawlResult:
        started = perf_counter()
        results: list[CrawlResult] = []
        for keyword in dict.fromkeys(k.strip() for k in keywords if k.strip()):
            results.append(
                await self.crawl_keyword(
                    keyword=keyword,
                    cod_objeto=cod_objeto,
                    cod_departamento=cod_departamento,
                    cod_tipo_proceso=cod_tipo_proceso,
                )
            )

        duration = perf_counter() - started
        return BulkCrawlResult(
            results=results,
            fetched=sum(item.fetched for item in results),
            inserted=sum(item.inserted for item in results),
            duplicates=sum(item.duplicates for item in results),
            failed=sum(item.failed for item in results),
            duration_seconds=round(duration, 4),
        )
