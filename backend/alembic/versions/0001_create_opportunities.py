"""create opportunities table

Revision ID: 0001_create_opportunities
Revises:
Create Date: 2026-05-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_opportunities"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seace_id", sa.Integer(), nullable=False),
        sa.Column("entity_name", sa.String(length=512), nullable=True),
        sa.Column("process_type", sa.String(length=255), nullable=True),
        sa.Column("nomenclature", sa.String(length=255), nullable=True),
        sa.Column("object_type", sa.String(length=100), nullable=True),
        sa.Column("item_description", sa.Text(), nullable=True),
        sa.Column("cubso_code", sa.String(length=64), nullable=True),
        sa.Column("cubso_description", sa.Text(), nullable=True),
        sa.Column("process_summary", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seace_id"),
    )
    op.create_index(op.f("ix_opportunities_seace_id"), "opportunities", ["seace_id"], unique=False)
    op.create_index(op.f("ix_opportunities_entity_name"), "opportunities", ["entity_name"], unique=False)
    op.create_index(op.f("ix_opportunities_process_type"), "opportunities", ["process_type"], unique=False)
    op.create_index(op.f("ix_opportunities_nomenclature"), "opportunities", ["nomenclature"], unique=False)
    op.create_index(op.f("ix_opportunities_object_type"), "opportunities", ["object_type"], unique=False)
    op.create_index(op.f("ix_opportunities_cubso_code"), "opportunities", ["cubso_code"], unique=False)
    op.create_index(op.f("ix_opportunities_publish_date"), "opportunities", ["publish_date"], unique=False)
    op.create_index(op.f("ix_opportunities_end_date"), "opportunities", ["end_date"], unique=False)
    op.create_index(op.f("ix_opportunities_keyword"), "opportunities", ["keyword"], unique=False)
    op.create_index("ix_opportunities_keyword_end_date", "opportunities", ["keyword", "end_date"], unique=False)
    op.create_index("ix_opportunities_entity_keyword", "opportunities", ["entity_name", "keyword"], unique=False)
    op.create_index("ix_opportunities_process_type_end_date", "opportunities", ["process_type", "end_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_opportunities_process_type_end_date", table_name="opportunities")
    op.drop_index("ix_opportunities_entity_keyword", table_name="opportunities")
    op.drop_index("ix_opportunities_keyword_end_date", table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_keyword"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_end_date"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_publish_date"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_cubso_code"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_object_type"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_nomenclature"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_process_type"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_entity_name"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_seace_id"), table_name="opportunities")
    op.drop_table("opportunities")
