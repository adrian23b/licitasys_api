"""create identity tables

Revision ID: 0002_create_identity_tables
Revises: 0001_create_opportunities
Create Date: 2026-06-08 00:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_create_identity_tables"
down_revision = "0001_create_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corporate_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("ruc", sa.String(length=11), nullable=False),
        sa.Column("corporate_email", sa.String(length=255), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("profile_hash", sa.String(length=66), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verification_tx_hash", sa.String(length=66), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corporate_email"),
        sa.UniqueConstraint("ruc"),
        sa.UniqueConstraint("wallet_address"),
    )
    op.create_index(op.f("ix_corporate_identities_corporate_email"), "corporate_identities", ["corporate_email"])
    op.create_index(op.f("ix_corporate_identities_profile_hash"), "corporate_identities", ["profile_hash"])
    op.create_index(op.f("ix_corporate_identities_ruc"), "corporate_identities", ["ruc"])
    op.create_index(op.f("ix_corporate_identities_verification_status"), "corporate_identities", ["verification_status"])
    op.create_index(op.f("ix_corporate_identities_wallet_address"), "corporate_identities", ["wallet_address"])

    op.create_table(
        "identity_nonces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["identity_id"], ["corporate_identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nonce"),
    )
    op.create_index(op.f("ix_identity_nonces_consumed"), "identity_nonces", ["consumed"])
    op.create_index(op.f("ix_identity_nonces_expires_at"), "identity_nonces", ["expires_at"])
    op.create_index(op.f("ix_identity_nonces_identity_id"), "identity_nonces", ["identity_id"])
    op.create_index(op.f("ix_identity_nonces_wallet_address"), "identity_nonces", ["wallet_address"])

    op.create_table(
        "identity_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["identity_id"], ["corporate_identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_identity_tokens_active", "identity_tokens", ["token_hash", "expires_at", "revoked"])
    op.create_index(op.f("ix_identity_tokens_expires_at"), "identity_tokens", ["expires_at"])
    op.create_index(op.f("ix_identity_tokens_identity_id"), "identity_tokens", ["identity_id"])
    op.create_index(op.f("ix_identity_tokens_revoked"), "identity_tokens", ["revoked"])
    op.create_index(op.f("ix_identity_tokens_token_hash"), "identity_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index(op.f("ix_identity_tokens_token_hash"), table_name="identity_tokens")
    op.drop_index(op.f("ix_identity_tokens_revoked"), table_name="identity_tokens")
    op.drop_index(op.f("ix_identity_tokens_identity_id"), table_name="identity_tokens")
    op.drop_index(op.f("ix_identity_tokens_expires_at"), table_name="identity_tokens")
    op.drop_index("ix_identity_tokens_active", table_name="identity_tokens")
    op.drop_table("identity_tokens")
    op.drop_index(op.f("ix_identity_nonces_wallet_address"), table_name="identity_nonces")
    op.drop_index(op.f("ix_identity_nonces_identity_id"), table_name="identity_nonces")
    op.drop_index(op.f("ix_identity_nonces_expires_at"), table_name="identity_nonces")
    op.drop_index(op.f("ix_identity_nonces_consumed"), table_name="identity_nonces")
    op.drop_table("identity_nonces")
    op.drop_index(op.f("ix_corporate_identities_wallet_address"), table_name="corporate_identities")
    op.drop_index(op.f("ix_corporate_identities_verification_status"), table_name="corporate_identities")
    op.drop_index(op.f("ix_corporate_identities_ruc"), table_name="corporate_identities")
    op.drop_index(op.f("ix_corporate_identities_profile_hash"), table_name="corporate_identities")
    op.drop_index(op.f("ix_corporate_identities_corporate_email"), table_name="corporate_identities")
    op.drop_table("corporate_identities")
