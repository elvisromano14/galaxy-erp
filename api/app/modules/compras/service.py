import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_monto
from app.core.errores import GalaxyERPException
from app.modules.admin.models import Proveedor
from app.modules.admin.service import AdminService
from app.modules.compras.models import CompraFactura, CompraFacturaDetalle
from app.modules.compras.schemas import CompraFacturaCreate
from app.modules.cxc_cxp.models import CuentaPorPagar
from app.modules.impuestos.models import ComprobanteRetencionIva
from app.modules.inventario.service import InventarioService


class ComprasService:
    @staticmethod
    async def registrar_compra(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: CompraFacturaCreate,
    ) -> CompraFactura:
        # 1. Validar proveedor y obtener reglas de retención
        prov = await session.get(Proveedor, data.proveedor_id)
        if not prov or prov.company_id != company_id:
            raise GalaxyERPException(
                code="PROVEEDOR_NO_ENCONTRADO",
                title="Proveedor no válido",
                status=404,
                detail="El proveedor no existe en la empresa activa.",
            )

        # 2. Resolver tasa de cambio
        tasa = data.tasa_cambio
        if not tasa:
            tasa = await AdminService.obtener_tasa_actual(session, data.fecha_emision, "USD")

        # 3. Calcular bases imponibles, exento e IVA
        base_imponible = Decimal("0.00")
        monto_exento = Decimal("0.00")
        monto_iva = Decimal("0.00")

        detalles_data: list[tuple[uuid.UUID, Decimal, Decimal, Decimal, Decimal]] = []

        for item in data.items:
            subtotal = cuantizar_monto(item.cantidad * item.costo_unitario)
            if item.alicuota_iva > Decimal("0.00"):
                base_imponible += subtotal
                iva_linea = cuantizar_monto(subtotal * (item.alicuota_iva / Decimal("100.00")))
                monto_iva += iva_linea
            else:
                monto_exento += subtotal

            detalles_data.append(
                (item.product_id, item.cantidad, item.costo_unitario, item.alicuota_iva, subtotal)
            )

        total_doc = base_imponible + monto_exento + monto_iva

        if data.moneda.upper() == "USD":
            total_usd = total_doc
            total_ves = cuantizar_monto(total_doc * tasa)
            monto_iva_ves = cuantizar_monto(monto_iva * tasa)
            base_ves = cuantizar_monto(base_imponible * tasa)
        else:
            total_ves = total_doc
            total_usd = cuantizar_monto(total_doc / tasa)
            monto_iva_ves = monto_iva
            base_ves = base_imponible

        # 4. Retenciones configurables según la ficha del proveedor
        aplica_ret_iva = prov.retiene_iva
        pct_ret_iva = prov.porcentaje_retencion_iva if aplica_ret_iva else Decimal("0.00")
        monto_ret_iva = (
            cuantizar_monto(monto_iva * (pct_ret_iva / Decimal("100.00")))
            if aplica_ret_iva
            else Decimal("0.00")
        )
        monto_ret_iva_ves = (
            cuantizar_monto(monto_iva_ves * (pct_ret_iva / Decimal("100.00")))
            if aplica_ret_iva
            else Decimal("0.00")
        )

        aplica_ret_islr = prov.retiene_islr
        pct_ret_islr = prov.porcentaje_retencion_islr if aplica_ret_islr else Decimal("0.00")
        monto_ret_islr = (
            cuantizar_monto(base_imponible * (pct_ret_islr / Decimal("100.00")))
            if aplica_ret_islr
            else Decimal("0.00")
        )

        # 5. Guardar cabecera de compra
        compra = CompraFactura(
            company_id=company_id,
            proveedor_id=prov.id,
            warehouse_id=data.warehouse_id,
            numero_factura=data.numero_factura.strip().upper(),
            numero_control=data.numero_control.strip().upper() if data.numero_control else None,
            fecha_emision=data.fecha_emision,
            tasa_cambio=tasa,
            moneda=data.moneda.upper(),
            monto_exento=monto_exento,
            base_imponible=base_imponible,
            monto_iva=monto_iva,
            total_usd=total_usd,
            total_ves=total_ves,
            aplica_retencion_iva=aplica_ret_iva,
            porcentaje_retencion_iva=pct_ret_iva,
            monto_retencion_iva=monto_ret_iva,
            aplica_retencion_islr=aplica_ret_islr,
            porcentaje_retencion_islr=pct_ret_islr,
            monto_retencion_islr=monto_ret_islr,
            estado="REGISTRADA",
            created_by=usuario_id,
        )
        session.add(compra)
        await session.flush()

        # 6. Guardar líneas y mover inventario (Kardex COMPRA)
        for prod_id, cant, costo, ali, subt in detalles_data:
            det = CompraFacturaDetalle(
                compra_id=compra.id,
                product_id=prod_id,
                cantidad=cant,
                costo_unitario=costo,
                alicuota_iva=ali,
                subtotal=subt,
            )
            session.add(det)

            # Entrada a inventario
            await InventarioService.registrar_movimiento(
                session=session,
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                product_id=prod_id,
                tipo="COMPRA",
                documento_id=compra.id,
                documento_tipo="COMPRA",
                cantidad=cant,  # Positivo: incrementa existencia
                costo_std=costo,
                usuario_id=usuario_id,
                motivo=f"Factura Compra {compra.numero_factura} de {prov.razon_social}",
            )

        # 7. Crear obligación en CxP (restando retención practicada)
        neto_usd = total_usd - monto_ret_iva - monto_ret_islr
        neto_ves = (
            total_ves
            - cuantizar_monto(monto_ret_iva * tasa)
            - cuantizar_monto(monto_ret_islr * tasa)
        )

        cxp = CuentaPorPagar(
            company_id=company_id,
            proveedor_id=prov.id,
            compra_id=compra.id,
            monto_total_usd=total_usd,
            monto_total_ves=total_ves,
            saldo_pendiente_usd=max(Decimal("0.00"), neto_usd),
            saldo_pendiente_ves=max(Decimal("0.00"), neto_ves),
            fecha_emision=data.fecha_emision,
            fecha_vencimiento=data.fecha_emision,
            estado="PENDIENTE",
        )
        session.add(cxp)

        # 8. Generar comprobante de retención IVA si aplicó
        if aplica_ret_iva and monto_ret_iva_ves > Decimal("0.00"):
            periodo = data.fecha_emision.strftime("%Y%m")
            num_comp = f"{periodo}000{uuid.uuid4().hex[:5].upper()}"
            comp_iva = ComprobanteRetencionIva(
                company_id=company_id,
                proveedor_id=prov.id,
                compra_id=compra.id,
                numero_comprobante=num_comp,
                periodo_fiscal=periodo,
                fecha_emision=data.fecha_emision,
                base_imponible_ves=base_ves,
                monto_iva_ves=monto_iva_ves,
                porcentaje_retencion=pct_ret_iva,
                monto_retenido_ves=monto_ret_iva_ves,
            )
            session.add(comp_iva)

        await session.flush()
        return compra

    @staticmethod
    async def listar_compras(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[CompraFactura]:
        stmt = (
            select(CompraFactura)
            .where(CompraFactura.company_id == company_id)
            .order_by(CompraFactura.fecha_emision.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()
