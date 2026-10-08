import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_cantidad
from app.core.errores import GalaxyERPException
from app.modules.inventario.models import (
    AjusteInventario,
    AjusteInventarioDetalle,
    StockBalance,
    StockMovement,
    TrasladoInventario,
    TrasladoInventarioDetalle,
)
from app.modules.inventario.schemas import (
    AjusteCreate,
    MovimientoManualCreate,
    TrasladoCreate,
)


class InventarioService:
    @staticmethod
    async def obtener_saldo(
        session: AsyncSession,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        for_update: bool = False,
    ) -> Decimal:
        stmt = select(StockBalance.cantidad).where(
            StockBalance.company_id == company_id,
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.product_id == product_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        res = await session.execute(stmt)
        val = res.scalar_one_or_none()
        return val if val is not None else Decimal("0.0000")

    @staticmethod
    async def registrar_movimiento(
        session: AsyncSession,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
        tipo: str,
        documento_id: uuid.UUID,
        documento_tipo: str,
        cantidad: Decimal,  # + entrada, - salida
        costo_std: Decimal,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
    ) -> StockMovement:
        """Registra un movimiento atómico en el Kardex y actualiza el saldo disponible."""
        cantidad_qty = cuantizar_cantidad(cantidad)

        # 1. Bloquear y consultar saldo actual
        saldo_actual = await InventarioService.obtener_saldo(
            session, company_id, warehouse_id, product_id, for_update=True
        )
        nuevo_saldo = saldo_actual + cantidad_qty

        if nuevo_saldo < Decimal("0.0000"):
            raise GalaxyERPException(
                code="STOCK_INSUFICIENTE",
                title="Stock insuficiente",
                status=400,
                detail=(
                    f"No hay suficiente existencia para realizar la operación. "
                    f"Saldo actual: {saldo_actual}, Solicitado: {abs(cantidad_qty)}"
                ),
            )

        # 2. Actualizar o insertar saldo
        stmt_balance = select(StockBalance).where(
            StockBalance.company_id == company_id,
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.product_id == product_id,
        )
        res_bal = await session.execute(stmt_balance)
        balance_obj = res_bal.scalar_one_or_none()

        if balance_obj:
            balance_obj.cantidad = nuevo_saldo
        else:
            balance_obj = StockBalance(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                cantidad=nuevo_saldo,
            )
            session.add(balance_obj)

        # 3. Insertar movimiento inmutable en kardex
        mov = StockMovement(
            company_id=company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            tipo=tipo.upper(),
            documento_id=documento_id,
            documento_tipo=documento_tipo.upper(),
            cantidad=cantidad_qty,
            costo_std=costo_std,
            motivo=motivo,
            created_by=usuario_id,
        )
        session.add(mov)
        await session.flush()
        return mov

    @staticmethod
    async def aplicar_movimiento_manual(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: MovimientoManualCreate,
    ) -> StockMovement:
        tipo = data.tipo.upper()
        if tipo not in ("CARGO", "DESCARGO"):
            raise GalaxyERPException(
                code="TIPO_MOVIMIENTO_INVALIDO",
                title="Tipo de movimiento inválido",
                status=400,
                detail="El tipo de movimiento manual debe ser CARGO o DESCARGO.",
            )

        signo = Decimal("1.0000") if tipo == "CARGO" else Decimal("-1.0000")
        cantidad_delta = data.cantidad * signo
        doc_id = uuid.uuid7()

        return await InventarioService.registrar_movimiento(
            session=session,
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            tipo=tipo,
            documento_id=doc_id,
            documento_tipo="MANUAL",
            cantidad=cantidad_delta,
            costo_std=data.costo_std,
            usuario_id=usuario_id,
            motivo=data.motivo,
        )

    @staticmethod
    async def ejecutar_traslado(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: TrasladoCreate,
    ) -> TrasladoInventario:
        if data.origen_warehouse_id == data.destino_warehouse_id:
            raise GalaxyERPException(
                code="ALMACEN_DESTINO_IGUAL",
                title="Almacenes idénticos",
                status=400,
                detail="El almacén de destino no puede ser el mismo de origen.",
            )

        traslado = TrasladoInventario(
            company_id=company_id,
            numero=f"TR-{uuid.uuid4().hex[:8].upper()}",
            origen_warehouse_id=data.origen_warehouse_id,
            destino_warehouse_id=data.destino_warehouse_id,
            motivo=data.motivo,
            created_by=usuario_id,
        )
        session.add(traslado)
        await session.flush()

        for item in data.items:
            det = TrasladoInventarioDetalle(
                traslado_id=traslado.id,
                product_id=item.product_id,
                cantidad=item.cantidad,
            )
            session.add(det)

            # 1. Salida en origen (TRASLADO_OUT)
            await InventarioService.registrar_movimiento(
                session=session,
                company_id=company_id,
                warehouse_id=data.origen_warehouse_id,
                product_id=item.product_id,
                tipo="TRASLADO_OUT",
                documento_id=traslado.id,
                documento_tipo="TRASLADO",
                cantidad=-item.cantidad,
                costo_std=Decimal("0.0000"),
                usuario_id=usuario_id,
                motivo=f"Traslado a {data.destino_warehouse_id}",
            )

            # 2. Entrada en destino (TRASLADO_IN)
            await InventarioService.registrar_movimiento(
                session=session,
                company_id=company_id,
                warehouse_id=data.destino_warehouse_id,
                product_id=item.product_id,
                tipo="TRASLADO_IN",
                documento_id=traslado.id,
                documento_tipo="TRASLADO",
                cantidad=item.cantidad,
                costo_std=Decimal("0.0000"),
                usuario_id=usuario_id,
                motivo=f"Traslado desde {data.origen_warehouse_id}",
            )

        await session.flush()
        return traslado

    @staticmethod
    async def ejecutar_ajuste(
        session: AsyncSession,
        company_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data: AjusteCreate,
    ) -> AjusteInventario:
        ajuste = AjusteInventario(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            numero=f"AJ-{uuid.uuid4().hex[:8].upper()}",
            motivo=data.motivo,
            estado="APROBADO",
            created_by=usuario_id,
        )
        session.add(ajuste)
        await session.flush()

        for item in data.items:
            saldo_sis = await InventarioService.obtener_saldo(
                session, company_id, data.warehouse_id, item.product_id, for_update=True
            )
            diferencia = item.cantidad_fisica - saldo_sis

            det = AjusteInventarioDetalle(
                ajuste_id=ajuste.id,
                product_id=item.product_id,
                cantidad_sistema=saldo_sis,
                cantidad_fisica=item.cantidad_fisica,
                diferencia=diferencia,
                costo_unitario=item.costo_unitario,
            )
            session.add(det)

            if diferencia != Decimal("0.0000"):
                tipo_kardex = "AJUSTE_POS" if diferencia > Decimal("0.0000") else "AJUSTE_NEG"
                await InventarioService.registrar_movimiento(
                    session=session,
                    company_id=company_id,
                    warehouse_id=data.warehouse_id,
                    product_id=item.product_id,
                    tipo=tipo_kardex,
                    documento_id=ajuste.id,
                    documento_tipo="AJUSTE",
                    cantidad=diferencia,
                    costo_std=item.costo_unitario,
                    usuario_id=usuario_id,
                    motivo=f"Ajuste {ajuste.numero}: {data.motivo}",
                )

        await session.flush()
        return ajuste

    @staticmethod
    async def listar_saldos(
        session: AsyncSession, company_id: uuid.UUID, warehouse_id: uuid.UUID | None = None
    ) -> Sequence[StockBalance]:
        stmt = select(StockBalance).where(StockBalance.company_id == company_id)
        if warehouse_id:
            stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def listar_kardex(
        session: AsyncSession,
        company_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
    ) -> Sequence[StockMovement]:
        stmt = (
            select(StockMovement)
            .where(StockMovement.company_id == company_id)
            .order_by(StockMovement.id.desc())
        )
        if product_id:
            stmt = stmt.where(StockMovement.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(StockMovement.warehouse_id == warehouse_id)
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def verificar_invariante_kardex(
        session: AsyncSession,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> bool:
        """Verifica la invariante matemática fundamental: saldo_actual == sum(movimientos)."""
        saldo_actual = await InventarioService.obtener_saldo(
            session, company_id, warehouse_id, product_id
        )
        stmt_sum = select(func.coalesce(func.sum(StockMovement.cantidad), Decimal("0.0000"))).where(
            StockMovement.company_id == company_id,
            StockMovement.warehouse_id == warehouse_id,
            StockMovement.product_id == product_id,
        )
        res_sum = await session.execute(stmt_sum)
        sum_kardex = res_sum.scalar_one()
        return saldo_actual == sum_kardex
