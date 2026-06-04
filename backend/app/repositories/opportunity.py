from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.schemas.opportunity import OpportunityCreate


class OpportunityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: int) -> Opportunity | None:
        result = await self.session.execute(
            select(Opportunity).where(Opportunity.id == opportunity_id)
        )
        return result.scalar_one_or_none()

    async def list_opportunities(
        self,
        *,
        keyword: str | None = None,
        entity: str | None = None,
        process_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Opportunity], int]:
        query = self._filtered_query(
            keyword=keyword,
            entity=entity,
            process_type=process_type,
            date_from=date_from,
            date_to=date_to,
        )
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        result = await self.session.execute(
            query.order_by(Opportunity.end_date.asc().nulls_last(), Opportunity.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def bulk_insert_ignore_duplicates(
        self,
        opportunities: list[OpportunityCreate],
    ) -> tuple[int, int]:
        if not opportunities:
            return 0, 0

        rows = [opportunity.model_dump() for opportunity in opportunities]
        statement = (
            insert(Opportunity)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Opportunity.seace_id])
            .returning(Opportunity.id)
        )
        result = await self.session.execute(statement)
        inserted = len(result.scalars().all())
        duplicates = len(rows) - inserted
        return inserted, duplicates

    def _filtered_query(
        self,
        *,
        keyword: str | None,
        entity: str | None,
        process_type: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Select[tuple[Opportunity]]:
        query = select(Opportunity)
        if keyword:
            query = query.where(Opportunity.keyword.ilike(f"%{keyword}%"))
        if entity:
            query = query.where(Opportunity.entity_name.ilike(f"%{entity}%"))
        if process_type:
            query = query.where(Opportunity.process_type.ilike(f"%{process_type}%"))
        if date_from:
            query = query.where(Opportunity.publish_date >= date_from)
        if date_to:
            query = query.where(Opportunity.publish_date <= date_to)
        return query
