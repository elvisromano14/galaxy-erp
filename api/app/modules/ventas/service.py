import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_monto
from app.core.errores import GalaxyERPException
from app.modules.admin.models import Cliente, Correlativo
from app.modules.admin.service import AdminService
from app.modules.cxc_cxp.models import CuentaPorCobrar
from app.modules.inventario.service import InventarioService
from app.modules.ventas.models import (
    FacturaVenta,
    FacturaVentaDetalle,
    NotaCreditoVenta,
    PresupuestoVenta,
    PresupuestoVentaDetalle,
)
from app.modules.ventas.schemas import (
    FacturaVentaCreate,
    NotaCreditoCreate,
    PresupuestoVentaCreate,
)


class VentasService:
    @staticmethod
    async def _obtener_siguiente_correlativo(
        session: AsyncSession, company_id: uuid.UUID, tipo: str
    ) -> int:
        stmt = (
            select(Correlativo)
            .where(Correlativo.company_id == company_id, Correlativo.tipo == tipo)
            .with_for_update()
        )
        res = await session.execute(stmt)
        corr = res.scalar_one_or_none()
        if not corr:
            corr = Correlativo(company_id=company_id, tipo=tipo, ultimo=1)
            session.add(corr)
            await session.flush()
            return 1
        corr.ultimo += 1
        await session.flush()
        return corr.ultimo

    @staticmethod
    async def crear_presupuesto(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: PresupuestoVentaCreate,
    ) -> PresupuestoVenta:
        cliente = await session.get(Cliente, data.cliente_id)
        if not cliente or cliente.company_id != company_id:
            raise GalaxyERPException(
                code="CLIENTE_NO_ENCONTRADO",
                title="Cliente no válido",
                status=404,
                detail="El cliente especificado no existe.",
            )

        tasa = await AdminService.obtener_tasa_actual(session, data.fecha, "USD")
        num_correlativo = await VentasService._obtener_siguiente_correlativo(
            session, company_id, "PRESUPUESTO"
        )
        numero_pres = f"COT-{num_correlativo:06d}"

        total_doc = Decimal("0.00")
        lineas = []
        for it in data.items:
            subt = cuantizar_monto(it.cantidad * it.precio_unitario)
            iva = (
                cuantizar_monto(subt * (it.alicuota_iva / Decimal("100.00")))
                if it.alicuota_iva > Decimal("0.00")
                else Decimal("0.00")
            )
            total_doc += subt + iva
            lineas.append((it.product_id, it.cantidad, it.precio_unitario, it.alicuota_iva, subt))

        total_usd = total_doc if data.moneda.upper() == "USD" else cuantizar_monto(total_doc / tasa)
        total_ves = cuantizar_monto(total_usd * tasa)

        presupuesto = PresupuestoVenta(
            company_id=company_id,
            cliente_id=cliente.id,
            warehouse_id=data.warehouse_id,
            vendedor_id=data.vendedor_id,
            numero=numero_pres,
            fecha=data.fecha,
            vigencia_dias=data.vigencia_dias,
            tasa_cambio=tasa,
            moneda=data.moneda.upper(),
            total_usd=total_usd,
            total_ves=total_ves,
            estado="BORRADOR",
            notas=data.notas,
            created_by=usuario_id,
        )
        session.add(presupuesto)
        await session.flush()

        for p_id, cant, precio, ali, subt in lineas:
            det = PresupuestoVentaDetalle(
                presupuesto_id=presupuesto.id,
                product_id=p_id,
                cantidad=cant,
                precio_unitario=precio,
                alicuota_iva=ali,
                subtotal=subt,
            )
            session.add(det)

        await session.flush()
        return presupuesto

    @staticmethod
    async def emitir_factura(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: FacturaVentaCreate,
    ) -> FacturaVenta:
        # 1. Validar cliente
        cliente = await session.get(Cliente, data.cliente_id)
        if not cliente or cliente.company_id != company_id:
            raise GalaxyERPException(
                code="CLIENTE_NO_ENCONTRADO",
                title="Cliente no válido",
                status=404,
                detail="El cliente especificado no existe en la empresa activa.",
            )

        # 2. Correlativos legales y fiscales
        num_factura_int = await VentasService._obtener_siguiente_correlativo(
            session, company_id, "FACTURA"
        )
        num_control_int = await VentasService._obtener_siguiente_correlativo(
            session, company_id, "CONTROL"
        )

        numero_factura = f"FAC-{num_factura_int:06d}"
        numero_control = f"00-{num_control_int:06d}"

        # 3. Tasa de cambio
        tasa = data.tasa_cambio
        if not tasa:
            tasa = await AdminService.obtener_tasa_actual(session, data.fecha_emision, "USD")

        # 4. Calcular bases, exento e IVA
        base_imponible = Decimal("0.00")
        monto_exento = Decimal("0.00")
        monto_iva = Decimal("0.00")
        detalles_data = []

        for item in data.items:
            subtotal = cuantizar_monto(item.cantidad * item.precio_unitario)
            if item.alicuota_iva > Decimal("0.00"):
                base_imponible += subtotal
                iva_linea = cuantizar_monto(subtotal * (item.alicuota_iva / Decimal("100.00")))
                monto_iva += iva_linea
            else:
                monto_exento += subtotal

            detalles_data.append(
                (item.product_id, item.cantidad, item.precio_unitario, item.alicuota_iva, subtotal)
            )

        total_doc = base_imponible + monto_exento + monto_iva

        if data.moneda.upper() == "USD":
            total_usd = total_doc
            total_ves = cuantizar_monto(total_doc * tasa)
        else:
            total_ves = total_doc
            total_usd = cuantizar_monto(total_doc / tasa)

        # 5. Retenciones configurables según la ficha del cliente
        cli_ret_iva = cliente.nos_retiene_iva
        pct_ret_iva = cliente.porcentaje_retencion_iva if cli_ret_iva else Decimal("0.00")
        monto_ret_iva = (
            cuantizar_monto(monto_iva * (pct_ret_iva / Decimal("100.00")))
            if cli_ret_iva
            else Decimal("0.00")
        )

        cli_ret_islr = cliente.nos_retiene_islr
        pct_ret_islr = cliente.porcentaje_retencion_islr if cli_ret_islr else Decimal("0.00")
        monto_ret_islr = (
            cuantizar_monto(base_imponible * (pct_ret_islr / Decimal("100.00")))
            if cli_ret_islr
            else Decimal("0.00")
        )

        saldo_neto_usd = total_usd - monto_ret_iva - monto_ret_islr
        saldo_neto_ves = (
            total_ves
            - cuantizar_monto(monto_ret_iva * tasa)
            - cuantizar_monto(monto_ret_islr * tasa)
        )

        # 6. Guardar factura
        factura = FacturaVenta(
            company_id=company_id,
            cliente_id=cliente.id,
            warehouse_id=data.warehouse_id,
            vendedor_id=data.vendedor_id,
            presupuesto_id=data.presupuesto_id,
            numero_factura=numero_factura,
            numero_control=numero_control,
            fecha_emision=data.fecha_emision,
            tasa_cambio=tasa,
            moneda=data.moneda.upper(),
            monto_exento=monto_exento,
            base_imponible=base_imponible,
            monto_iva=monto_iva,
            total_usd=total_usd,
            total_ves=total_ves,
            cliente_retiene_iva=cli_ret_iva,
            porcentaje_retencion_iva=pct_ret_iva,
            monto_retencion_iva=monto_ret_iva,
            cliente_retiene_islr=cli_ret_islr,
            porcentaje_retencion_islr=pct_ret_islr,
            monto_retencion_islr=monto_ret_islr,
            saldo_pendiente_usd=saldo_neto_usd,
            saldo_pendiente_ves=saldo_neto_ves,
            estado="EMITIDA",
            created_by=usuario_id,
        )
        session.add(factura)
        await session.flush()

        # 7. Descontar stock (Kardex VENTA) y guardar líneas
        for prod_id, cant, precio, ali, subt in detalles_data:
            det = FacturaVentaDetalle(
                factura_id=factura.id,
                product_id=prod_id,
                cantidad=cant,
                precio_unitario=precio,
                alicuota_iva=ali,
                subtotal=subt,
            )
            session.add(det)

            # Salida de inventario
            await InventarioService.registrar_movimiento(
                session=session,
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                product_id=prod_id,
                tipo="VENTA",
                documento_id=factura.id,
                documento_tipo="FACTURA",
                cantidad=-cant,  # Negativo: descuenta stock
                costo_std=Decimal("0.0000"),
                usuario_id=usuario_id,
                motivo=f"Factura de Venta {factura.numero_factura}",
            )

        # 8. Generar derecho en CxC
        cxc = CuentaPorCobrar(
            company_id=company_id,
            cliente_id=cliente.id,
            factura_id=factura.id,
            monto_total_usd=total_usd,
            monto_total_ves=total_ves,
            saldo_pendiente_usd=saldo_neto_usd,
            saldo_pendiente_ves=saldo_neto_ves,
            fecha_emision=data.fecha_emision,
            fecha_vencimiento=data.fecha_emision,
            estado="PENDIENTE",
        )
        session.add(cxc)

        # Si venía de presupuesto, marcarlo FACTURADO
        if data.presupuesto_id:
            pres = await session.get(PresupuestoVenta, data.presupuesto_id)
            if pres:
                pres.estado = "FACTURADO"

        await session.flush()
        return factura

    @staticmethod
    async def listar_facturas(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[FacturaVenta]:
        stmt = (
            select(FacturaVenta)
            .where(FacturaVenta.company_id == company_id)
            .order_by(FacturaVenta.fecha_emision.desc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def crear_nota_credito(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: NotaCreditoCreate,
    ) -> NotaCreditoVenta:
        factura = await session.get(FacturaVenta, data.factura_id)
        if not factura or factura.company_id != company_id:
            raise GalaxyERPException(
                code="FACTURA_NO_ENCONTRADA",
                title="Factura no encontrada",
                status=404,
                detail="La factura no existe.",
            )

        num_int = await VentasService._obtener_siguiente_correlativo(
            session, company_id, "NOTA_CREDITO"
        )
        num_ctrl = await VentasService._obtener_siguiente_correlativo(
            session, company_id, "CONTROL"
        )

        nc = NotaCreditoVenta(
            company_id=company_id,
            factura_id=factura.id,
            numero_nota=f"NC-{num_int:06d}",
            numero_control=f"00-{num_ctrl:06d}",
            fecha_emision=data.fecha_emision,
            motivo=data.motivo,
            monto_total_usd=data.monto_total_usd,
            monto_total_ves=data.monto_total_ves,
            created_by=usuario_id,
        )
        session.add(nc)

        # Ajustar saldo en factura
        factura.saldo_pendiente_usd = max(
            Decimal("0.00"), factura.saldo_pendiente_usd - data.monto_total_usd
        )
        factura.saldo_pendiente_ves = max(
            Decimal("0.00"), factura.saldo_pendiente_ves - data.monto_total_ves
        )

        await session.flush()
        return nc

    @staticmethod
    async def obtener_factura_pdf(
        session: AsyncSession,
        company_id: uuid.UUID,
        factura_id: uuid.UUID,
    ) -> bytes:
        from app.modules.admin.models import Cliente, Company, Product
        from app.modules.reportes.pdf import generar_factura_pdf

        factura = await session.get(FacturaVenta, factura_id)
        if not factura or factura.company_id != company_id:
            raise GalaxyERPException(
                code="FACTURA_NO_ENCONTRADA",
                title="Factura no encontrada",
                status=404,
                detail="La factura no existe.",
            )

        empresa = await session.get(Company, company_id)
        cliente = await session.get(Cliente, factura.cliente_id)

        res_det = await session.execute(
            select(FacturaVentaDetalle, Product)
            .join(Product, FacturaVentaDetalle.product_id == Product.id)
            .where(FacturaVentaDetalle.factura_id == factura_id)
        )
        detalles_rows = res_det.all()

        detalles_data = [
            {
                "codigo": prod.codigo,
                "descripcion": prod.descripcion,
                "cantidad": float(det.cantidad),
                "precio_unitario": float(det.precio_unitario),
                "subtotal": float(det.subtotal),
            }
            for det, prod in detalles_rows
        ]

        empresa_dict = {
            "razon_social": empresa.razon_social if empresa else "EMPRESA",
            "rif": empresa.rif if empresa else "J-00000000-0",
            "direccion_fiscal": empresa.direccion_fiscal if empresa else "",
            "telefono": empresa.telefono if empresa else "",
        }
        cliente_dict = {
            "nombre": cliente.nombre if cliente else "CLIENTE",
            "tipo_identificacion": cliente.tipo_identificacion if cliente else "J",
            "identificacion": cliente.identificacion if cliente else "",
            "direccion": cliente.direccion if cliente else "",
        }
        condicion = "CREDITO" if factura.saldo_pendiente_usd > Decimal("0.00") else "CONTADO"
        factura_dict = {
            "numero": factura.numero_factura,
            "numero_control": factura.numero_control,
            "fecha_emision": factura.fecha_emision.isoformat(),
            "condicion_pago": condicion,
            "fecha_vencimiento": None,
            "base_imponible": float(factura.base_imponible),
            "monto_exento": float(factura.monto_exento),
            "monto_iva": float(factura.monto_iva),
            "monto_total": float(
                factura.total_usd if factura.moneda == "USD" else factura.total_ves
            ),
            "moneda": factura.moneda,
            "tasa_cambio": float(factura.tasa_cambio),
        }

        return generar_factura_pdf(
            empresa=empresa_dict,
            cliente=cliente_dict,
            factura=factura_dict,
            detalles=detalles_data,
        )
