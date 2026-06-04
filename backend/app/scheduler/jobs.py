from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.clients.seace import SeaceClient
from app.core.config import Settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.crawler import CrawlerService


logger = get_logger(__name__)


async def scheduled_crawl(settings: Settings) -> None:
    if not settings.scheduler_keywords:
        logger.warning("scheduled_crawl_skipped_no_keywords")
        return

    async with AsyncSessionLocal() as session:
        service = CrawlerService(session, SeaceClient(settings))
        result = await service.crawl_keywords(keywords=settings.scheduler_keywords)
        logger.info("scheduled_crawl_finished", **result.model_dump())


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Lima")
    scheduler.add_job(
        scheduled_crawl,
        trigger=IntervalTrigger(seconds=settings.crawler_interval),
        args=[settings],
        id="seace_periodic_crawl",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=None,
    )
    return scheduler
