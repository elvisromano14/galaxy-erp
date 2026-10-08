"""migracion de modelos para sincronizacion offline y preventa (Fase 6)

Revision ID: 0003_sincronizacion_offline
Revises: 0002_erp_fases_1_a_5
Create Date: 2026-10-08 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_sincronizacion_offline"
down_revision: str | None = "0002_erp_fases_1_a_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. sync_dispositivo
    op.create_table(
        "sync_dispositivo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("identificador_unico", sa.String(length=120), nullable=False),
        sa.Column("ultimo_token", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "company_id", "identificador_unico", name="uq_sync_dispositivo_identificador"
        ),
    )

    # 2. sync_operacion_log
    op.create_table(
        "sync_operacion_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dispositivo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sync_dispositivo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_op_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("numero_documento", sa.String(length=50), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", "client_op_id", name="uq_sync_operacion_client_op_id"),
    )

    # 3. sync_bloque_correlativo
    op.create_table(
        "sync_bloque_correlativo",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dispositivo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sync_dispositivo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo_documento", sa.String(length=30), nullable=False),
        sa.Column("serie", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("desde_numero", sa.BigInteger(), nullable=False),
        sa.Column("hasta_numero", sa.BigInteger(), nullable=False),
        sa.Column("ultimo_usado", sa.BigInteger(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Conceder permisos DML a erp_app
    tablas = ["sync_dispositivo", "sync_operacion_log", "sync_bloque_correlativo"]
    for t in tablas:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {t} TO erp_app")
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{t}' AND policyname = 'por_empresa'
                ) THEN
                    CREATE POLICY por_empresa ON {t}
                        USING (
                            company_id = NULLIF(
                                current_setting('app.company_id', true), ''
                            )::uuid
                        )
                        WITH CHECK (
                            company_id = NULLIF(
                                current_setting('app.company_id', true), ''
                            )::uuid
                        );
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    op.drop_table("sync_bloque_correlativo")
    op.drop_table("sync_operacion_log")
    op.drop_table("sync_dispositivo")
