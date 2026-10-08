import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_monto
from app.modules.admin.models import Cliente, Proveedor
from app.modules.compras.models import CompraFactura
from app.modules.impuestos.models import (
    ComprobanteRetencionIslr,
    ComprobanteRetencionIva,
)
from app.modules.impuestos.schemas import (
    LibroComprasFila,
    LibroComprasResponse,
    LibroVentasFila,
    LibroVentasResponse,
)
from app.modules.ventas.models import FacturaVenta


class ImpuestosService:
    @staticmethod
    async def generar_libro_ventas(
        session: AsyncSession, company_id: uuid.UUID, anio: int, mes: int
    ) -> LibroVentasResponse:
        stmt = (
            select(FacturaVenta, Cliente)
            .join(Cliente, FacturaVenta.cliente_id == Cliente.id)
            .where(
                FacturaVenta.company_id == company_id,
                extract("year", FacturaVenta.fecha_emision) == anio,
                extract("month", FacturaVenta.fecha_emision) == mes,
                FacturaVenta.estado == "EMITIDA",
            )
            .order_by(FacturaVenta.fecha_emision, FacturaVenta.numero_factura)
        )
        res = await session.execute(stmt)

        filas = []
        tot_ventas = Decimal("0.00")
        tot_exento = Decimal("0.00")
        tot_base = Decimal("0.00")
        tot_iva = Decimal("0.00")
        tot_ret = Decimal("0.00")

        for idx, (fac, cli) in enumerate(res.all(), start=1):
            exento_ves = cuantizar_monto(fac.monto_exento * fac.tasa_cambio)
            base_ves = cuantizar_monto(fac.base_imponible * fac.tasa_cambio)
            iva_ves = cuantizar_monto(fac.monto_iva * fac.tasa_cambio)
            ret_ves = cuantizar_monto(fac.monto_retencion_iva * fac.tasa_cambio)

            tot_ventas += fac.total_ves
            tot_exento += exento_ves
            tot_base += base_ves
            tot_iva += iva_ves
            tot_ret += ret_ves

            filas.append(
                LibroVentasFila(
                    operacion=idx,
                    fecha=fac.fecha_emision,
                    rif_cliente=f"{cli.tipo_identificacion}-{cli.identificacion}",
                    nombre_cliente=cli.nombre,
                    numero_factura=fac.numero_factura,
                    numero_control=fac.numero_control,
                    total_ventas_ves=fac.total_ves,
                    ventas_exentas_ves=exento_ves,
                    base_imponible_ves=base_ves,
                    iva_ves=iva_ves,
                    iva_retenido_ves=ret_ves,
                )
            )

        return LibroVentasResponse(
            periodo_fiscal=f"{anio:04d}-{mes:02d}",
            filas=filas,
            total_ventas_ves=tot_ventas,
            total_exento_ves=tot_exento,
            total_base_ves=tot_base,
            total_iva_ves=tot_iva,
            total_iva_retenido_ves=tot_ret,
        )

    @staticmethod
    async def generar_libro_compras(
        session: AsyncSession, company_id: uuid.UUID, anio: int, mes: int
    ) -> LibroComprasResponse:
        stmt = (
            select(CompraFactura, Proveedor)
            .join(Proveedor, CompraFactura.proveedor_id == Proveedor.id)
            .where(
                CompraFactura.company_id == company_id,
                extract("year", CompraFactura.fecha_emision) == anio,
                extract("month", CompraFactura.fecha_emision) == mes,
                CompraFactura.estado == "REGISTRADA",
            )
            .order_by(CompraFactura.fecha_emision, CompraFactura.numero_factura)
        )
        res = await session.execute(stmt)

        filas = []
        tot_compras = Decimal("0.00")
        tot_exento = Decimal("0.00")
        tot_base = Decimal("0.00")
        tot_iva = Decimal("0.00")
        tot_ret = Decimal("0.00")

        for idx, (compra, prov) in enumerate(res.all(), start=1):
            exento_ves = cuantizar_monto(compra.monto_exento * compra.tasa_cambio)
            base_ves = cuantizar_monto(compra.base_imponible * compra.tasa_cambio)
            iva_ves = cuantizar_monto(compra.monto_iva * compra.tasa_cambio)
            ret_ves = cuantizar_monto(compra.monto_retencion_iva * compra.tasa_cambio)

            tot_compras += compra.total_ves
            tot_exento += exento_ves
            tot_base += base_ves
            tot_iva += iva_ves
            tot_ret += ret_ves

            # Buscar comprobante emitido
            stmt_comp = select(ComprobanteRetencionIva.numero_comprobante).where(
                ComprobanteRetencionIva.company_id == company_id,
                ComprobanteRetencionIva.compra_id == compra.id,
            )
            res_comp = await session.execute(stmt_comp)
            num_comp = res_comp.scalar_one_or_none()

            filas.append(
                LibroComprasFila(
                    operacion=idx,
                    fecha=compra.fecha_emision,
                    rif_proveedor=prov.rif,
                    nombre_proveedor=prov.razon_social,
                    numero_factura=compra.numero_factura,
                    numero_control=compra.numero_control,
                    total_compras_ves=compra.total_ves,
                    compras_exentas_ves=exento_ves,
                    base_imponible_ves=base_ves,
                    iva_ves=iva_ves,
                    iva_retenido_ves=ret_ves,
                    numero_comprobante_retencion=num_comp,
                )
            )

        return LibroComprasResponse(
            periodo_fiscal=f"{anio:04d}-{mes:02d}",
            filas=filas,
            total_compras_ves=tot_compras,
            total_exento_ves=tot_exento,
            total_base_ves=tot_base,
            total_iva_ves=tot_iva,
            total_iva_retenido_ves=tot_ret,
        )

    @staticmethod
    async def listar_retenciones_iva(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[ComprobanteRetencionIva]:
        stmt = (
            select(ComprobanteRetencionIva)
            .where(ComprobanteRetencionIva.company_id == company_id)
            .order_by(ComprobanteRetencionIva.fecha_emision.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def listar_retenciones_islr(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[ComprobanteRetencionIslr]:
        stmt = (
            select(ComprobanteRetencionIslr)
            .where(ComprobanteRetencionIslr.company_id == company_id)
            .order_by(ComprobanteRetencionIslr.fecha_emision.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def obtener_retencion_iva_pdf(
        session: AsyncSession, company_id: uuid.UUID, comprobante_id: uuid.UUID
    ) -> bytes:
        from app.core.errores import GalaxyERPException
        from app.modules.admin.models import Company
        from app.modules.compras.models import CompraFactura
        from app.modules.reportes.pdf import generar_comprobante_retencion_pdf

        comp = await session.get(ComprobanteRetencionIva, comprobante_id)
        if not comp or comp.company_id != company_id:
            raise GalaxyERPException(
                code="COMPROBANTE_NO_ENCONTRADO",
                title="Comprobante no encontrado",
                status=404,
                detail="El comprobante de retención no existe.",
            )

        agente = await session.get(Company, company_id)
        sujeto = await session.get(Proveedor, comp.proveedor_id)
        compra = await session.get(CompraFactura, comp.compra_id)

        agente_dict = {
            "razon_social": agente.razon_social if agente else "EMPRESA AGENTE",
            "rif": agente.rif if agente else "J-00000000-0",
            "direccion_fiscal": agente.direccion_fiscal if agente else "",
        }
        sujeto_dict = {
            "nombre": sujeto.razon_social if sujeto else "PROVEEDOR SUJETO",
            "tipo_identificacion": "",
            "identificacion": sujeto.rif if sujeto else "",
            "direccion": sujeto.direccion if sujeto else "",
        }
        comp_dict = {
            "numero": comp.numero_comprobante,
            "fecha_emision": comp.fecha_emision.isoformat(),
            "periodo_fiscal": comp.periodo_fiscal,
            "factura_numero": compra.numero_factura if compra else "S/N",
            "numero_control": compra.numero_control if compra else "S/N",
            "base_imponible": float(comp.base_imponible_ves),
            "monto_impuesto": float(comp.monto_iva_ves),
            "porcentaje": float(comp.porcentaje_retencion),
            "monto_retenido": float(comp.monto_retenido_ves),
        }

        return generar_comprobante_retencion_pdf(
            agente=agente_dict,
            sujeto=sujeto_dict,
            comprobante=comp_dict,
            tipo_retencion="IVA",
        )
