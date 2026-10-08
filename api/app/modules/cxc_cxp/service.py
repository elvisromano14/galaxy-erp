import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import GalaxyERPException
from app.core.tiempo import hoy_ccs
from app.modules.bancos.schemas import TransaccionBancariaCreate
from app.modules.bancos.service import BancosService
from app.modules.cxc_cxp.models import (
    CobroCliente,
    CuentaPorCobrar,
    CuentaPorPagar,
    PagoProveedor,
)
from app.modules.cxc_cxp.schemas import (
    AntiguedadBucket,
    CobroClienteCreate,
    PagoProveedorCreate,
)
from app.modules.ventas.models import FacturaVenta


class CxcCxpService:
    @staticmethod
    async def aplicar_cobro(
        session: AsyncSession,
        company_id: uuid.UUID,
        data: CobroClienteCreate,
    ) -> CobroCliente:
        cxc = await session.get(CuentaPorCobrar, data.cxc_id)
        if not cxc or cxc.company_id != company_id:
            raise GalaxyERPException(
                code="CXC_NO_ENCONTRADA",
                title="Cuenta por cobrar no encontrada",
                status=404,
                detail="La cuenta por cobrar especificada no existe.",
            )

        if cxc.estado == "PAGADA":
            raise GalaxyERPException(
                code="CXC_YA_PAGADA",
                title="Cuenta ya pagada",
                status=400,
                detail="Esta cuenta por cobrar ya se encuentra completamente liquidada.",
            )

        recibo_num = f"RC-{uuid.uuid4().hex[:8].upper()}"
        cobro = CobroCliente(
            company_id=company_id,
            cliente_id=cxc.cliente_id,
            cxc_id=cxc.id,
            numero_recibo=recibo_num,
            fecha=data.fecha,
            monto_cobrado_usd=data.monto_cobrado_usd,
            monto_cobrado_ves=data.monto_cobrado_ves,
            retencion_iva_deducida=data.retencion_iva_deducida,
            retencion_islr_deducida=data.retencion_islr_deducida,
            instrumento_pago_id=data.instrumento_pago_id,
            cuenta_bancaria_id=data.cuenta_bancaria_id,
            referencia=data.referencia,
            notas=data.notas,
        )
        session.add(cobro)

        # Total abonado al saldo
        abono_usd = (
            data.monto_cobrado_usd + data.retencion_iva_deducida + data.retencion_islr_deducida
        )
        cxc.saldo_pendiente_usd = max(Decimal("0.00"), cxc.saldo_pendiente_usd - abono_usd)
        cxc.saldo_pendiente_ves = max(
            Decimal("0.00"), cxc.saldo_pendiente_ves - data.monto_cobrado_ves
        )

        if cxc.saldo_pendiente_usd == Decimal("0.00"):
            cxc.estado = "PAGADA"
        else:
            cxc.estado = "PARCIAL"

        # Reflejar en la factura
        factura = await session.get(FacturaVenta, cxc.factura_id)
        if factura:
            factura.saldo_pendiente_usd = cxc.saldo_pendiente_usd
            factura.saldo_pendiente_ves = cxc.saldo_pendiente_ves

        # Si involucra banco, registrar movimiento de tesorería
        if data.cuenta_bancaria_id and data.monto_cobrado_ves > Decimal("0.00"):
            await BancosService.registrar_transaccion(
                session=session,
                company_id=company_id,
                data=TransaccionBancariaCreate(
                    cuenta_id=data.cuenta_bancaria_id,
                    fecha=data.fecha,
                    tipo="INGRESO",
                    referencia=data.referencia or recibo_num,
                    monto=data.monto_cobrado_ves,
                    descripcion=(
                        f"Cobro {recibo_num} de CxC Factura "
                        f"{factura.numero_factura if factura else ''}"
                    ),
                ),
                doc_tipo="COBRO_CLIENTE",
                doc_id=cobro.id,
            )

        await session.flush()
        return cobro

    @staticmethod
    async def aplicar_pago(
        session: AsyncSession,
        company_id: uuid.UUID,
        data: PagoProveedorCreate,
    ) -> PagoProveedor:
        cxp = await session.get(CuentaPorPagar, data.cxp_id)
        if not cxp or cxp.company_id != company_id:
            raise GalaxyERPException(
                code="CXP_NO_ENCONTRADA",
                title="Cuenta por pagar no encontrada",
                status=404,
                detail="La cuenta por pagar especificada no existe.",
            )

        if cxp.estado == "PAGADA":
            raise GalaxyERPException(
                code="CXP_YA_PAGADA",
                title="Cuenta ya pagada",
                status=400,
                detail="Esta cuenta por pagar ya se encuentra completamente liquidada.",
            )

        comp_num = f"OP-{uuid.uuid4().hex[:8].upper()}"
        pago = PagoProveedor(
            company_id=company_id,
            proveedor_id=cxp.proveedor_id,
            cxp_id=cxp.id,
            numero_comprobante=comp_num,
            fecha=data.fecha,
            monto_pagado_usd=data.monto_pagado_usd,
            monto_pagado_ves=data.monto_pagado_ves,
            retencion_iva_aplicada=data.retencion_iva_aplicada,
            retencion_islr_aplicada=data.retencion_islr_aplicada,
            instrumento_pago_id=data.instrumento_pago_id,
            cuenta_bancaria_id=data.cuenta_bancaria_id,
            referencia=data.referencia,
            notas=data.notas,
        )
        session.add(pago)

        abono_usd = (
            data.monto_pagado_usd + data.retencion_iva_aplicada + data.retencion_islr_aplicada
        )
        cxp.saldo_pendiente_usd = max(Decimal("0.00"), cxp.saldo_pendiente_usd - abono_usd)
        cxp.saldo_pendiente_ves = max(
            Decimal("0.00"), cxp.saldo_pendiente_ves - data.monto_pagado_ves
        )

        if cxp.saldo_pendiente_usd == Decimal("0.00"):
            cxp.estado = "PAGADA"
        else:
            cxp.estado = "PARCIAL"

        # Si involucra banco, registrar egreso de tesorería
        if data.cuenta_bancaria_id and data.monto_pagado_ves > Decimal("0.00"):
            await BancosService.registrar_transaccion(
                session=session,
                company_id=company_id,
                data=TransaccionBancariaCreate(
                    cuenta_id=data.cuenta_bancaria_id,
                    fecha=data.fecha,
                    tipo="EGRESO",
                    referencia=data.referencia or comp_num,
                    monto=data.monto_pagado_ves,
                    descripcion=f"Pago {comp_num} de CxP compra",
                ),
                doc_tipo="PAGO_PROVEEDOR",
                doc_id=pago.id,
            )

        await session.flush()
        return pago

    @staticmethod
    async def listar_cxc(session: AsyncSession, company_id: uuid.UUID) -> Sequence[CuentaPorCobrar]:
        stmt = (
            select(CuentaPorCobrar)
            .where(CuentaPorCobrar.company_id == company_id)
            .order_by(CuentaPorCobrar.fecha_vencimiento)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def listar_cxp(session: AsyncSession, company_id: uuid.UUID) -> Sequence[CuentaPorPagar]:
        stmt = (
            select(CuentaPorPagar)
            .where(CuentaPorPagar.company_id == company_id)
            .order_by(CuentaPorPagar.fecha_vencimiento)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def calcular_antiguedad_cxc(
        session: AsyncSession, company_id: uuid.UUID, fecha_corte: date | None = None
    ) -> AntiguedadBucket:
        corte = fecha_corte or hoy_ccs()
        stmt = select(CuentaPorCobrar).where(
            CuentaPorCobrar.company_id == company_id,
            CuentaPorCobrar.saldo_pendiente_usd > Decimal("0.00"),
        )
        res = await session.execute(stmt)
        bucket = AntiguedadBucket()

        for c in res.scalars().all():
            dias = (corte - c.fecha_vencimiento).days
            monto = c.saldo_pendiente_usd
            bucket.total += monto
            if dias <= 30:
                bucket.dias_0_30 += monto
            elif dias <= 60:
                bucket.dias_31_60 += monto
            elif dias <= 90:
                bucket.dias_61_90 += monto
            else:
                bucket.dias_mas_90 += monto

        return bucket
