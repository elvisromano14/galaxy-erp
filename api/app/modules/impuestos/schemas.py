import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ComprobanteIvaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    proveedor_id: uuid.UUID
    compra_id: uuid.UUID
    numero_comprobante: str
    periodo_fiscal: str
    fecha_emision: date
    base_imponible_ves: Decimal
    monto_iva_ves: Decimal
    porcentaje_retencion: Decimal
    monto_retenido_ves: Decimal
    created_at: datetime


class LibroVentasFila(BaseModel):
    operacion: int
    fecha: date
    rif_cliente: str
    nombre_cliente: str
    numero_factura: str
    numero_control: str
    total_ventas_ves: Decimal
    ventas_exentas_ves: Decimal
    base_imponible_ves: Decimal
    iva_ves: Decimal
    iva_retenido_ves: Decimal


class LibroVentasResponse(BaseModel):
    periodo_fiscal: str
    filas: list[LibroVentasFila]
    total_ventas_ves: Decimal
    total_exento_ves: Decimal
    total_base_ves: Decimal
    total_iva_ves: Decimal
    total_iva_retenido_ves: Decimal


class LibroComprasFila(BaseModel):
    operacion: int
    fecha: date
    rif_proveedor: str
    nombre_proveedor: str
    numero_factura: str
    numero_control: str | None
    total_compras_ves: Decimal
    compras_exentas_ves: Decimal
    base_imponible_ves: Decimal
    iva_ves: Decimal
    iva_retenido_ves: Decimal
    numero_comprobante_retencion: str | None


class LibroComprasResponse(BaseModel):
    periodo_fiscal: str
    filas: list[LibroComprasFila]
    total_compras_ves: Decimal
    total_exento_ves: Decimal
    total_base_ves: Decimal
    total_iva_ves: Decimal
    total_iva_retenido_ves: Decimal
