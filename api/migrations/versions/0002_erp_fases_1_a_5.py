"""migracion integral de modelos para Fases 1 a 5
(Administracion, Inventario, Compras/Ventas, Finanzas, Impuestos)

Revision ID: 0002_erp_fases_1_a_5
Revises: 0001_tenant_base
Create Date: 2026-10-08 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_erp_fases_1_a_5"
down_revision: str | None = "0001_tenant_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Alter company para campos de retención y contacto
    op.add_column("company", sa.Column("direccion_fiscal", sa.Text(), nullable=True))
    op.add_column("company", sa.Column("telefono", sa.String(length=50), nullable=True))
    op.add_column(
        "company",
        sa.Column("agente_retencion_iva", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "company",
        sa.Column(
            "porcentaje_retencion_iva_default",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="75.00",
        ),
    )

    # 2. Tasa de Cambio (Bimoneda VES/USD)
    op.create_table(
        "tasa_cambio",
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("fuente", sa.String(length=20), nullable=False, server_default="BCV"),
        sa.Column("valor", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("fecha", "moneda", "fuente"),
    )

    # 3. Categoría (Jerárquica)
    op.create_table(
        "categoria",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["categoria.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_categoria_company_codigo"),
    )

    # 4. Producto
    op.create_table(
        "product",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alicuota_iva_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("codigo_barras", sa.String(length=40), nullable=True),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.Column("unidad", sa.String(length=10), nullable=False, server_default="UND"),
        sa.Column("costo_estandar", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("precio_base_usd", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("minimo", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("maximo", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.ForeignKeyConstraint(["categoria_id"], ["categoria.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["alicuota_iva_id"], ["alicuota_iva.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_product_company_codigo"),
    )

    # 5. Proveedor (Retenciones configurables)
    op.create_table(
        "proveedor",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rif", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column(
            "contribuyente", sa.String(length=20), nullable=False, server_default="ORDINARIO"
        ),
        sa.Column("retiene_iva", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "porcentaje_retencion_iva",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="75.00",
        ),
        sa.Column("retiene_islr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_islr",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("dias_credito", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "rif", name="uq_proveedor_company_rif"),
    )

    # 6. Zona
    op.create_table(
        "zona",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_zona_company_codigo"),
    )

    # 7. Vendedor
    op.create_table(
        "vendedor",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("zona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("comision_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zona_id"], ["zona.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_vendedor_company_codigo"),
    )

    # 8. Cliente (Retenciones configurables)
    op.create_table(
        "cliente",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_identificacion", sa.String(length=2), nullable=False, server_default="V"),
        sa.Column("identificacion", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column(
            "contribuyente", sa.String(length=20), nullable=False, server_default="ORDINARIO"
        ),
        sa.Column("nos_retiene_iva", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_iva",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="75.00",
        ),
        sa.Column("nos_retiene_islr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_islr",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("zona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("limite_credito", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("dias_credito", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zona_id"], ["zona.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["vendedor.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "company_id", "identificacion", name="uq_cliente_company_identificacion"
        ),
    )

    # 9. Instrumento de Pago
    op.create_table(
        "instrumento_pago",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="VES"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_instrumento_pago_company_codigo"),
    )

    # 10. Tipo de Operación
    op.create_table(
        "tipo_operacion",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("modulo", sa.String(length=30), nullable=False),
        sa.Column("afecta_inventario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("signo_inventario", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_tipo_operacion_company_codigo"),
    )

    # 11. Saldos de Inventario
    op.create_table(
        "stock_balance",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_id", "warehouse_id", "product_id"),
        sa.CheckConstraint("cantidad >= 0", name="chk_stock_balance_cantidad_positiva"),
    )

    # 12. Movimientos de Inventario (Kardex inmutable)
    op.create_table(
        "stock_movement",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("documento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("documento_tipo", sa.String(length=30), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_std", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
    )

    # 13. Ajuste de Inventario
    op.create_table(
        "ajuste_inventario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="BORRADOR"),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero", name="uq_ajuste_inventario_company_numero"),
    )
    op.create_table(
        "ajuste_inventario_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ajuste_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad_sistema", sa.Numeric(18, 4), nullable=False),
        sa.Column("cantidad_fisica", sa.Numeric(18, 4), nullable=False),
        sa.Column("diferencia", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False),
        sa.ForeignKeyConstraint(["ajuste_id"], ["ajuste_inventario.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 14. Traslado de Inventario
    op.create_table(
        "traslado_inventario",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("origen_warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destino_warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="COMPLETADO"),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origen_warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destino_warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero", name="uq_traslado_inventario_company_numero"),
    )
    op.create_table(
        "traslado_inventario_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("traslado_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.ForeignKeyConstraint(["traslado_id"], ["traslado_inventario.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 15. Orden de Compra
    op.create_table(
        "orden_compra",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="BORRADOR"),
        sa.Column("total_estimado", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero", name="uq_orden_compra_company_numero"),
    )
    op.create_table(
        "orden_compra_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("orden_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["orden_id"], ["orden_compra.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 16. Factura de Compra (Recepción)
    op.create_table(
        "compra_factura",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("orden_compra_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("numero_factura", sa.String(length=30), nullable=False),
        sa.Column("numero_control", sa.String(length=30), nullable=True),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("tasa_cambio", sa.Numeric(18, 6), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("monto_exento", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("base_imponible", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_iva", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("aplica_retencion_iva", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_iva",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("monto_retencion_iva", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("aplica_retencion_islr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_islr",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("monto_retencion_islr", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="REGISTRADA"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["orden_compra_id"], ["orden_compra.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "company_id",
            "proveedor_id",
            "numero_factura",
            name="uq_compra_factura_proveedor_numero",
        ),
    )
    op.create_table(
        "compra_factura_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("compra_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("alicuota_iva", sa.Numeric(5, 2), nullable=False, server_default="16.00"),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["compra_id"], ["compra_factura.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 17. Presupuesto de Venta
    op.create_table(
        "presupuesto_venta",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("numero", sa.String(length=20), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("vigencia_dias", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("tasa_cambio", sa.Numeric(18, 6), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("total_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="BORRADOR"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["vendedor.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero", name="uq_presupuesto_venta_company_numero"),
    )
    op.create_table(
        "presupuesto_venta_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("presupuesto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("alicuota_iva", sa.Numeric(5, 2), nullable=False, server_default="16.00"),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["presupuesto_id"], ["presupuesto_venta.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 18. Factura de Venta (Fiscal SENIAT)
    op.create_table(
        "factura_venta",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendedor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("presupuesto_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("numero_factura", sa.String(length=20), nullable=False),
        sa.Column("numero_control", sa.String(length=20), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("tasa_cambio", sa.Numeric(18, 6), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("monto_exento", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("base_imponible", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_iva", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("cliente_retiene_iva", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_iva",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("monto_retencion_iva", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("cliente_retiene_islr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "porcentaje_retencion_islr",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("monto_retencion_islr", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="EMITIDA"),
        sa.Column("saldo_pendiente_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("saldo_pendiente_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["vendedor.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["presupuesto_id"], ["presupuesto_venta.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero_factura", name="uq_factura_venta_company_numero"),
    )
    op.create_table(
        "factura_venta_detalle",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(18, 4), nullable=False),
        sa.Column("alicuota_iva", sa.Numeric(5, 2), nullable=False, server_default="16.00"),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["factura_id"], ["factura_venta.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
    )

    # 19. Nota de Crédito de Venta
    op.create_table(
        "nota_credito_venta",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_nota", sa.String(length=20), nullable=False),
        sa.Column("numero_control", sa.String(length=20), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("monto_total_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_total_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["factura_id"], ["factura_venta.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "numero_nota", name="uq_nota_credito_company_numero"),
    )

    # 20. Bancos y Cuentas
    op.create_table(
        "cuenta_bancaria",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("banco_nombre", sa.String(length=100), nullable=False),
        sa.Column("numero_cuenta", sa.String(length=50), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False, server_default="CORRIENTE"),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="VES"),
        sa.Column("saldo_actual", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "company_id", "numero_cuenta", name="uq_cuenta_bancaria_company_numero"
        ),
    )
    op.create_table(
        "transaccion_bancaria",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cuenta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("referencia", sa.String(length=50), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("tasa_cambio", sa.Numeric(18, 6), nullable=False, server_default="1.000000"),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("conciliado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("documento_origen_tipo", sa.String(length=30), nullable=True),
        sa.Column("documento_origen_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cuenta_id"], ["cuenta_bancaria.id"], ondelete="CASCADE"),
    )

    # 21. Cuentas por Cobrar y Cobros
    op.create_table(
        "cuenta_por_cobrar",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monto_total_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_total_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_pendiente_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_pendiente_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="PENDIENTE"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["factura_id"], ["factura_venta.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "factura_id", name="uq_cxc_company_factura"),
    )
    op.create_table(
        "cobro_cliente",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cxc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_recibo", sa.String(length=20), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("monto_cobrado_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_cobrado_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "retencion_iva_deducida",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "retencion_islr_deducida",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("instrumento_pago_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cuenta_bancaria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("referencia", sa.String(length=100), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cxc_id"], ["cuenta_por_cobrar.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["instrumento_pago_id"], ["instrumento_pago.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_bancaria_id"], ["cuenta_bancaria.id"], ondelete="SET NULL"
        ),
    )

    # 22. Cuentas por Pagar y Pagos
    op.create_table(
        "cuenta_por_pagar",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compra_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monto_total_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_total_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_pendiente_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_pendiente_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="PENDIENTE"),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["compra_id"], ["compra_factura.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "compra_id", name="uq_cxp_company_compra"),
    )
    op.create_table(
        "pago_proveedor",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cxp_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_comprobante", sa.String(length=20), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("monto_pagado_usd", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_pagado_ves", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "retencion_iva_aplicada",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "retencion_islr_aplicada",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("instrumento_pago_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cuenta_bancaria_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("referencia", sa.String(length=100), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cxp_id"], ["cuenta_por_pagar.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["instrumento_pago_id"], ["instrumento_pago.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["cuenta_bancaria_id"], ["cuenta_bancaria.id"], ondelete="SET NULL"
        ),
    )

    # 23. Comprobantes de Retención Fiscal SENIAT
    op.create_table(
        "comprobante_retencion_iva",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compra_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_comprobante", sa.String(length=20), nullable=False),
        sa.Column("periodo_fiscal", sa.String(length=6), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("base_imponible_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_iva_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("porcentaje_retencion", sa.Numeric(5, 2), nullable=False),
        sa.Column("monto_retenido_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["compra_id"], ["compra_factura.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "company_id", "numero_comprobante", name="uq_retencion_iva_company_numero"
        ),
    )
    op.create_table(
        "comprobante_retencion_islr",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proveedor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compra_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero_comprobante", sa.String(length=20), nullable=False),
        sa.Column("periodo_fiscal", sa.String(length=6), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("concepto", sa.String(length=100), nullable=False),
        sa.Column("base_imponible_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column("porcentaje_retencion", sa.Numeric(5, 2), nullable=False),
        sa.Column("monto_retenido_ves", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proveedor_id"], ["proveedor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["compra_id"], ["compra_factura.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "company_id", "numero_comprobante", name="uq_retencion_islr_company_numero"
        ),
    )


def downgrade() -> None:
    pass
