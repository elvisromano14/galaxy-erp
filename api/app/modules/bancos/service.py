import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dinero import cuantizar_monto
from app.core.errores import GalaxyERPException
from app.modules.bancos.models import CuentaBancaria, TransaccionBancaria
from app.modules.bancos.schemas import (
    CuentaBancariaCreate,
    TransaccionBancariaCreate,
)


class BancosService:
    @staticmethod
    async def crear_cuenta(
        session: AsyncSession, company_id: uuid.UUID, data: CuentaBancariaCreate
    ) -> CuentaBancaria:
        cuenta = CuentaBancaria(
            company_id=company_id,
            banco_nombre=data.banco_nombre.strip(),
            numero_cuenta=data.numero_cuenta.strip(),
            tipo=data.tipo.strip().upper(),
            moneda=data.moneda.strip().upper(),
            saldo_actual=cuantizar_monto(data.saldo_inicial),
        )
        session.add(cuenta)
        await session.flush()
        return cuenta

    @staticmethod
    async def listar_cuentas(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[CuentaBancaria]:
        stmt = (
            select(CuentaBancaria)
            .where(CuentaBancaria.company_id == company_id)
            .order_by(CuentaBancaria.banco_nombre)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def registrar_transaccion(
        session: AsyncSession,
        company_id: uuid.UUID,
        data: TransaccionBancariaCreate,
        doc_tipo: str | None = None,
        doc_id: uuid.UUID | None = None,
    ) -> TransaccionBancaria:
        cuenta = await session.get(CuentaBancaria, data.cuenta_id)
        if not cuenta or cuenta.company_id != company_id:
            raise GalaxyERPException(
                code="CUENTA_NO_ENCONTRADA",
                title="Cuenta bancaria no encontrada",
                status=404,
                detail="La cuenta bancaria especificada no existe en la empresa activa.",
            )

        tipo = data.tipo.upper()
        if tipo not in ("INGRESO", "EGRESO"):
            raise GalaxyERPException(
                code="TIPO_TRANSACCION_INVALIDO",
                title="Tipo inválido",
                status=400,
                detail="El tipo de transacción debe ser INGRESO o EGRESO.",
            )

        monto_qty = cuantizar_monto(data.monto)
        if tipo == "INGRESO":
            cuenta.saldo_actual += monto_qty
        else:
            if cuenta.saldo_actual < monto_qty:
                raise GalaxyERPException(
                    code="SALDO_BANCARIO_INSUFICIENTE",
                    title="Saldo bancario insuficiente",
                    status=400,
                    detail=(
                        f"Saldo en cuenta ({cuenta.saldo_actual}) es menor "
                        f"al monto a debitar ({monto_qty})."
                    ),
                )
            cuenta.saldo_actual -= monto_qty

        tx = TransaccionBancaria(
            company_id=company_id,
            cuenta_id=cuenta.id,
            fecha=data.fecha,
            tipo=tipo,
            referencia=data.referencia.strip(),
            monto=monto_qty,
            tasa_cambio=data.tasa_cambio,
            descripcion=data.descripcion.strip(),
            documento_origen_tipo=doc_tipo,
            documento_origen_id=doc_id,
        )
        session.add(tx)
        await session.flush()
        return tx

    @staticmethod
    async def listar_transacciones(
        session: AsyncSession, company_id: uuid.UUID, cuenta_id: uuid.UUID | None = None
    ) -> Sequence[TransaccionBancaria]:
        stmt = (
            select(TransaccionBancaria)
            .where(TransaccionBancaria.company_id == company_id)
            .order_by(TransaccionBancaria.fecha.desc())
        )
        if cuenta_id:
            stmt = stmt.where(TransaccionBancaria.cuenta_id == cuenta_id)
        res = await session.execute(stmt)
        return res.scalars().all()
