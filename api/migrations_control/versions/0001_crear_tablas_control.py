"""crear tablas iniciales del plano de control

Revision ID: 0001_control_init
Revises:
Create Date: 2026-10-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_control_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Tabla tenant
    op.create_table(
        "tenant",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("db_host", sa.String(length=120), nullable=False, server_default="127.0.0.1"),
        sa.Column("db_port", sa.Integer(), nullable=False, server_default="6432"),
        sa.Column("db_name", sa.String(length=63), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="aprovisionando"),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("es_canario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schema_rev", sa.String(length=64), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z][a-z0-9-]{1,38}[a-z0-9]$'",
            name="chk_tenant_slug_formato",
        ),
        sa.CheckConstraint(
            "estado IN ('aprovisionando', 'activo', 'suspendido', 'archivado', 'fallido')",
            name="chk_tenant_estado_valido",
        ),
        sa.UniqueConstraint("slug", name="uq_tenant_slug"),
        sa.UniqueConstraint("db_name", name="uq_tenant_db_name"),
    )

    # 2. Tabla tenant_modulo
    op.create_table(
        "tenant_modulo",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modulo", sa.String(length=40), nullable=False),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("vence_en", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "modulo"),
    )

    # 3. Tabla tenant_job
    op.create_table(
        "tenant_job",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="EN_CURSO"),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "iniciado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("terminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="SET NULL"),
    )

    # 4. Tabla plataforma_admin
    op.create_table(
        "plataforma_admin",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("email", name="uq_plataforma_admin_email"),
    )


def downgrade() -> None:
    op.drop_table("plataforma_admin")
    op.drop_table("tenant_job")
    op.drop_table("tenant_modulo")
    op.drop_table("tenant")
