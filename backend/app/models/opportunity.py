from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seace_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    entity_name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    process_type: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    nomenclature: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    object_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cubso_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cubso_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


Index("ix_opportunities_keyword_end_date", Opportunity.keyword, Opportunity.end_date)
Index("ix_opportunities_entity_keyword", Opportunity.entity_name, Opportunity.keyword)
Index("ix_opportunities_process_type_end_date", Opportunity.process_type, Opportunity.end_date)
