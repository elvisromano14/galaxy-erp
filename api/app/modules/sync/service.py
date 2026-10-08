"""Servicio de lógica de negocio para sincronización offline y preventa de campo."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_monto
from app.core.errores import GalaxyERPException
from app.core.tiempo import ahora
from app.modules.admin.models import (
    AlicuotaIva,
    Cliente,
    Correlativo,
    Product,
    TasaCambio,
    Warehouse,
)
from app.modules.inventario.models import StockBalance
from app.modules.sync.models import (
    DispositivoSync,
    SyncBloqueCorrelativo,
    SyncOperacionLog,
)
from app.modules.sync.schemas import (
    BatchOperacionesSyncRequest,
    BatchOperacionesSyncResponse,
    BloqueCorrelativoRequest,
    BloqueCorrelativoResponse,
    CatalogosSyncResponse,
    DispositivoSyncCreate,
    OperacionSyncResultado,
)
from app.modules.ventas.models import (
    PresupuestoVenta,
    PresupuestoVentaDetalle,
)


class SyncService:
    @staticmethod
    async def registrar_dispositivo(
        session: AsyncSession, company_id: uuid.UUID, data: DispositivoSyncCreate
    ) -> DispositivoSync:
        # Verificar si ya existe
        stmt = select(DispositivoSync).where(
            DispositivoSync.company_id == company_id,
            DispositivoSync.identificador_unico == data.identificador_unico,
        )
        res = await session.execute(stmt)
        existente = res.scalar_one_or_none()
        if existente:
            existente.nombre = data.nombre
            existente.usuario_id = data.usuario_id
            existente.activo = True
            await session.flush()
            return existente

        disp = DispositivoSync(
            company_id=company_id,
            usuario_id=data.usuario_id,
            nombre=data.nombre,
            identificador_unico=data.identificador_unico,
        )
        session.add(disp)
        await session.flush()
        return disp

    @staticmethod
    async def descargar_catalogos(
        session: AsyncSession, company_id: uuid.UUID, desde_token: int = 0
    ) -> CatalogosSyncResponse:
        # 1. Productos
        res_p = await session.execute(
            select(Product).where(Product.company_id == company_id, Product.activo.is_(True))
        )
        prods = [
            {
                "id": str(p.id),
                "codigo": p.codigo,
                "codigo_barras": p.codigo_barras,
                "descripcion": p.descripcion,
                "unidad": p.unidad,
                "precio_base_usd": float(p.precio_base_usd),
                "alicuota_iva_id": str(p.alicuota_iva_id),
            }
            for p in res_p.scalars().all()
        ]

        # 2. Clientes
        res_c = await session.execute(
            select(Cliente).where(Cliente.company_id == company_id, Cliente.activo.is_(True))
        )
        clis = [
            {
                "id": str(c.id),
                "tipo_identificacion": c.tipo_identificacion,
                "identificacion": c.identificacion,
                "nombre": c.nombre,
                "direccion": c.direccion,
                "telefono": c.telefono,
                "aplica_retencion_iva": c.nos_retiene_iva,
                "porcentaje_retencion_iva": float(c.porcentaje_retencion_iva),
            }
            for c in res_c.scalars().all()
        ]

        # 3. Almacenes
        res_w = await session.execute(
            select(Warehouse).where(Warehouse.company_id == company_id, Warehouse.activo.is_(True))
        )
        alms = [
            {"id": str(w.id), "codigo": w.codigo, "nombre": w.nombre} for w in res_w.scalars().all()
        ]

        # 4. Existencias
        res_s = await session.execute(
            select(StockBalance).where(StockBalance.company_id == company_id)
        )
        stks = [
            {
                "warehouse_id": str(sb.warehouse_id),
                "product_id": str(sb.product_id),
                "cantidad": float(sb.cantidad),
            }
            for sb in res_s.scalars().all()
        ]

        # 5. Alícuotas
        res_a = await session.execute(select(AlicuotaIva))
        alics = [
            {"id": str(a.id), "codigo": a.codigo, "porcentaje": float(a.porcentaje)}
            for a in res_a.scalars().all()
        ]

        # 6. Tasa del día
        hoy = date.today()
        stmt_t = (
            select(TasaCambio)
            .where(TasaCambio.fecha <= hoy, TasaCambio.moneda == "USD")
            .order_by(TasaCambio.fecha.desc())
            .limit(1)
        )
        res_t = await session.execute(stmt_t)
        tasa_obj = res_t.scalar_one_or_none()
        tasa_val = tasa_obj.valor if tasa_obj else None

        nuevo_token = int(ahora().timestamp())

        return CatalogosSyncResponse(
            sync_token=nuevo_token,
            productos=prods,
            clientes=clis,
            almacenes=alms,
            existencias=stks,
            alicuotas_iva=alics,
            tasa_actual_usd=tasa_val,
        )

    @staticmethod
    async def solicitar_bloque(
        session: AsyncSession, company_id: uuid.UUID, data: BloqueCorrelativoRequest
    ) -> BloqueCorrelativoResponse:
        disp = await session.get(DispositivoSync, data.dispositivo_id)
        if not disp or disp.company_id != company_id or not disp.activo:
            raise GalaxyERPException(
                code="DISPOSITIVO_INVALIDO",
                title="Dispositivo no autorizado",
                status=403,
                detail="El dispositivo no existe o se encuentra inactivo.",
            )

        stmt = (
            select(Correlativo)
            .where(
                Correlativo.company_id == company_id,
                Correlativo.tipo == data.tipo_documento,
                Correlativo.serie == data.serie,
            )
            .with_for_update()
        )
        res = await session.execute(stmt)
        corr = res.scalar_one_or_none()
        if not corr:
            corr = Correlativo(
                company_id=company_id,
                tipo=data.tipo_documento,
                serie=data.serie,
                ultimo=0,
            )
            session.add(corr)
            await session.flush()

        desde = corr.ultimo + 1
        hasta = corr.ultimo + data.cantidad
        corr.ultimo = hasta

        bloque = SyncBloqueCorrelativo(
            company_id=company_id,
            dispositivo_id=data.dispositivo_id,
            tipo_documento=data.tipo_documento,
            serie=data.serie,
            desde_numero=desde,
            hasta_numero=hasta,
            ultimo_usado=desde - 1,
            activo=True,
        )
        session.add(bloque)
        await session.flush()

        return BloqueCorrelativoResponse.model_validate(bloque)

    @staticmethod
    async def procesar_operaciones(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: BatchOperacionesSyncRequest,
    ) -> BatchOperacionesSyncResponse:
        disp = await session.get(DispositivoSync, data.dispositivo_id)
        if not disp or disp.company_id != company_id or not disp.activo:
            raise GalaxyERPException(
                code="DISPOSITIVO_INVALIDO",
                title="Dispositivo no autorizado",
                status=403,
                detail="El dispositivo no existe o se encuentra inactivo.",
            )

        disp.ultimo_acceso = ahora()
        resultados: list[OperacionSyncResultado] = []

        for op in data.operaciones:
            # 1. Verificar idempotencia
            stmt = select(SyncOperacionLog).where(
                SyncOperacionLog.company_id == company_id,
                SyncOperacionLog.client_op_id == op.client_op_id,
            )
            res_op = await session.execute(stmt)
            previo = res_op.scalar_one_or_none()
            if previo:
                resultados.append(
                    OperacionSyncResultado(
                        client_op_id=op.client_op_id,
                        estado="DUPLICADA",
                        documento_id=previo.documento_id,
                        numero=previo.numero_documento,
                        error=None,
                    )
                )
                continue

            # 2. Procesar según tipo
            if op.tipo == "PEDIDO_VENTA":
                try:
                    async with session.begin_nested():
                        payload = op.payload
                        cliente_id = uuid.UUID(payload["cliente_id"])
                        warehouse_id = uuid.UUID(payload["warehouse_id"])
                        vendedor_id = (
                            uuid.UUID(payload["vendedor_id"])
                            if payload.get("vendedor_id")
                            else None
                        )
                        tasa = op.tasa_usada or Decimal("1.000000")

                        # Número asignado
                        num_propuesto = payload.get("numero")
                        if not num_propuesto:
                            # Asignar secuencial seguro
                            num_propuesto = f"PED-{int(ahora().timestamp())}"

                        pedido = PresupuestoVenta(
                            company_id=company_id,
                            cliente_id=cliente_id,
                            warehouse_id=warehouse_id,
                            vendedor_id=vendedor_id,
                            numero=num_propuesto,
                            fecha=op.creado_en.date(),
                            tasa_cambio=tasa,
                            moneda=payload.get("moneda", "USD"),
                            estado="APROBADO",
                            notas=f"Pedido offline desde móvil: {disp.nombre}",
                            created_by=usuario_id,
                        )
                        session.add(pedido)
                        await session.flush()

                        tot_usd = Decimal("0.00")
                        for item in payload.get("items", []):
                            pid = uuid.UUID(item["product_id"])
                            cant = Decimal(str(item["cantidad"]))
                            precio = Decimal(str(item["precio_unitario"]))
                            subt = cuantizar_monto(cant * precio)
                            tot_usd += subt
                            session.add(
                                PresupuestoVentaDetalle(
                                    presupuesto_id=pedido.id,
                                    product_id=pid,
                                    cantidad=cant,
                                    precio_unitario=precio,
                                    subtotal=subt,
                                )
                            )
                        pedido.total_usd = tot_usd
                        pedido.total_ves = cuantizar_monto(tot_usd * tasa)
                        await session.flush()

                        log_entry = SyncOperacionLog(
                            company_id=company_id,
                            dispositivo_id=disp.id,
                            client_op_id=op.client_op_id,
                            tipo=op.tipo,
                            estado="APLICADA",
                            documento_id=pedido.id,
                            numero_documento=pedido.numero,
                            payload=payload,
                            error=None,
                        )
                        session.add(log_entry)
                        await session.flush()

                    resultados.append(
                        OperacionSyncResultado(
                            client_op_id=op.client_op_id,
                            estado="APLICADA",
                            documento_id=pedido.id,
                            numero=pedido.numero,
                            error=None,
                        )
                    )
                except Exception as exc:
                    log_entry = SyncOperacionLog(
                        company_id=company_id,
                        dispositivo_id=disp.id,
                        client_op_id=op.client_op_id,
                        tipo=op.tipo,
                        estado="RECHAZADA",
                        documento_id=None,
                        numero_documento=None,
                        payload=op.payload,
                        error=str(exc),
                    )
                    session.add(log_entry)
                    await session.flush()

                    resultados.append(
                        OperacionSyncResultado(
                            client_op_id=op.client_op_id,
                            estado="RECHAZADA",
                            documento_id=None,
                            numero=None,
                            error=str(exc),
                        )
                    )
            else:
                resultados.append(
                    OperacionSyncResultado(
                        client_op_id=op.client_op_id,
                        estado="RECHAZADA",
                        documento_id=None,
                        numero=None,
                        error=f"Tipo de operación no soportado: {op.tipo}",
                    )
                )

        return BatchOperacionesSyncResponse(resultados=resultados)
