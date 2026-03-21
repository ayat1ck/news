"""Add VK source support and reserve MAX publish target.

Revision ID: 20260318_0001
Revises:
Create Date: 2026-03-18 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260318_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'vk'")
        op.execute("ALTER TYPE publishtarget ADD VALUE IF NOT EXISTS 'max'")

    with op.batch_alter_table("sources") as batch_op:
        batch_op.add_column(sa.Column("vk_domain", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("vk_domain")

