"""crear esquema base de datos de cliente tenant

Revision ID: 0001_tenant_base
Revises:
Create Date: 2026-10-08 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_tenant_base"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Company
    op.create_table(
        "company",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("rif", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column(
            "contribuyente",
            sa.String(length=20),
            nullable=False,
            server_default="ORDINARIO",
        ),
        sa.Column("moneda_base", sa.String(length=3), nullable=False, server_default="VES"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("rif", name="uq_company_rif"),
    )

    # 2. Warehouse
    op.create_table(
        "warehouse",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_warehouse_company_codigo"),
    )

    # 3. Alicuota IVA
    op.create_table(
        "alicuota_iva",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("porcentaje", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("fuente", sa.Text(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_alicuota_iva_codigo"),
    )

    # 4. Correlativo
    op.create_table(
        "correlativo",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("serie", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("ultimo", sa.BigInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "tipo", "serie"),
    )

    # 5. Idempotency Keys
    op.create_table(
        "idempotency_keys",
        sa.Column("llave", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hash_cuerpo", sa.Text(), nullable=False),
        sa.Column("respuesta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado_http", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 6. Usuario
    op.create_table(
        "usuario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("nombre_completo", sa.String(length=200), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("intentos_fallidos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
    )

    # 7. Rol
    op.create_table(
        "rol",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("es_sistema", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
    )

    # 8. Permiso
    op.create_table(
        "permiso",
        sa.Column("codigo", sa.String(length=60), primary_key=True),
        sa.Column("modulo", sa.String(length=40), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
    )

    # 9. Rol Permiso
    op.create_table(
        "rol_permiso",
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permiso_codigo", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permiso_codigo"], ["permiso.codigo"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rol_id", "permiso_codigo"),
    )

    # 10. Usuario Rol
    op.create_table(
        "usuario_rol",
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id", "rol_id"),
    )

    # 11. Sesion Refresh
    op.create_table(
        "sesion_refresh",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
    )

    # 12. Audit Log (append-only)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entidad", sa.String(length=50), nullable=False),
        sa.Column("entidad_id", sa.String(length=100), nullable=False),
        sa.Column("accion", sa.String(length=30), nullable=False),
        sa.Column("datos_previos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("datos_nuevos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("trace_id", sa.String(length=100), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("sesion_refresh")
    op.drop_table("usuario_rol")
    op.drop_table("rol_permiso")
    op.drop_table("permiso")
    op.drop_table("rol")
    op.drop_table("usuario")
    op.drop_table("idempotency_keys")
    op.drop_table("correlativo")
    op.drop_table("alicuota_iva")
    op.drop_table("warehouse")
    op.drop_table("company")
