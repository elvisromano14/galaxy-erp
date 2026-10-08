import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import GalaxyERPException
from app.modules.admin.models import (
    Categoria,
    Cliente,
    InstrumentoPago,
    Product,
    Proveedor,
    TasaCambio,
    TipoOperacion,
    Vendedor,
    Warehouse,
    Zona,
)
from app.modules.admin.schemas import (
    CategoriaCreate,
    ClienteCreate,
    InstrumentoPagoCreate,
    ProductCreate,
    ProductUpdate,
    ProveedorCreate,
    TasaCambioCreate,
    TipoOperacionCreate,
    VendedorCreate,
    WarehouseCreate,
    ZonaCreate,
)


class AdminService:
    # --- TASA DE CAMBIO ---
    @staticmethod
    async def registrar_tasa(session: AsyncSession, data: TasaCambioCreate) -> TasaCambio:
        tasa = TasaCambio(
            fecha=data.fecha,
            moneda=data.moneda.upper(),
            fuente=data.fuente.upper(),
            valor=data.valor,
        )
        session.add(tasa)
        await session.flush()
        return tasa

    @staticmethod
    async def obtener_tasa_actual(
        session: AsyncSession, fecha_ref: date, moneda: str = "USD"
    ) -> Decimal:
        stmt = (
            select(TasaCambio.valor)
            .where(TasaCambio.moneda == moneda.upper(), TasaCambio.fecha <= fecha_ref)
            .order_by(TasaCambio.fecha.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        val = res.scalar_one_or_none()
        if not val:
            raise GalaxyERPException(
                code="TASA_NO_DISPONIBLE",
                title="Tasa de cambio no encontrada",
                status=404,
                detail=f"No hay tasa de cambio registrada para {moneda} en o antes de {fecha_ref}.",
            )
        return val

    # --- CATEGORIAS ---
    @staticmethod
    async def crear_categoria(
        session: AsyncSession, company_id: uuid.UUID, data: CategoriaCreate
    ) -> Categoria:
        cat = Categoria(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
            descripcion=data.descripcion,
            parent_id=data.parent_id,
        )
        session.add(cat)
        await session.flush()
        return cat

    @staticmethod
    async def listar_categorias(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[Categoria]:
        stmt = (
            select(Categoria).where(Categoria.company_id == company_id).order_by(Categoria.codigo)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    # --- PRODUCTOS ---
    @staticmethod
    async def crear_producto(
        session: AsyncSession, company_id: uuid.UUID, data: ProductCreate
    ) -> Product:
        # Validar existencia de categoría
        cat = await session.get(Categoria, data.categoria_id)
        if not cat or cat.company_id != company_id:
            raise GalaxyERPException(
                code="CATEGORIA_INVALIDA",
                title="Categoría inexistente",
                status=400,
                detail="La categoría especificada no existe en la empresa activa.",
            )

        prod = Product(
            company_id=company_id,
            categoria_id=data.categoria_id,
            alicuota_iva_id=data.alicuota_iva_id,
            codigo=data.codigo.strip().upper(),
            codigo_barras=data.codigo_barras.strip() if data.codigo_barras else None,
            descripcion=data.descripcion.strip(),
            unidad=data.unidad.strip().upper(),
            costo_estandar=data.costo_estandar,
            precio_base_usd=data.precio_base_usd,
            minimo=data.minimo,
            maximo=data.maximo,
        )
        session.add(prod)
        await session.flush()
        return prod

    @staticmethod
    async def listar_productos(
        session: AsyncSession, company_id: uuid.UUID, categoria_id: uuid.UUID | None = None
    ) -> Sequence[Product]:
        stmt = select(Product).where(Product.company_id == company_id)
        if categoria_id:
            stmt = stmt.where(Product.categoria_id == categoria_id)
        stmt = stmt.order_by(Product.codigo)
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def actualizar_producto(
        session: AsyncSession,
        company_id: uuid.UUID,
        product_id: uuid.UUID,
        data: ProductUpdate,
    ) -> Product:
        prod = await session.get(Product, product_id)
        if not prod or prod.company_id != company_id:
            raise GalaxyERPException(
                code="PRODUCTO_NO_ENCONTRADO",
                title="Producto no encontrado",
                status=404,
                detail="El producto no existe en esta empresa.",
            )

        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(prod, campo, valor)

        prod.version += 1
        await session.flush()
        return prod

    # --- PROVEEDORES ---
    @staticmethod
    async def crear_proveedor(
        session: AsyncSession, company_id: uuid.UUID, data: ProveedorCreate
    ) -> Proveedor:
        prov = Proveedor(
            company_id=company_id,
            rif=data.rif.strip().upper(),
            razon_social=data.razon_social.strip(),
            direccion=data.direccion,
            telefono=data.telefono,
            email=data.email,
            contribuyente=data.contribuyente.upper(),
            retiene_iva=data.retiene_iva,
            porcentaje_retencion_iva=data.porcentaje_retencion_iva,
            retiene_islr=data.retiene_islr,
            porcentaje_retencion_islr=data.porcentaje_retencion_islr,
            dias_credito=data.dias_credito,
        )
        session.add(prov)
        await session.flush()
        return prov

    @staticmethod
    async def listar_proveedores(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[Proveedor]:
        stmt = (
            select(Proveedor)
            .where(Proveedor.company_id == company_id)
            .order_by(Proveedor.razon_social)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    # --- CLIENTES ---
    @staticmethod
    async def crear_cliente(
        session: AsyncSession, company_id: uuid.UUID, data: ClienteCreate
    ) -> Cliente:
        cli = Cliente(
            company_id=company_id,
            tipo_identificacion=data.tipo_identificacion.upper(),
            identificacion=data.identificacion.strip().upper(),
            nombre=data.nombre.strip(),
            direccion=data.direccion,
            telefono=data.telefono,
            email=data.email,
            contribuyente=data.contribuyente.upper(),
            nos_retiene_iva=data.nos_retiene_iva,
            porcentaje_retencion_iva=data.porcentaje_retencion_iva,
            nos_retiene_islr=data.nos_retiene_islr,
            porcentaje_retencion_islr=data.porcentaje_retencion_islr,
            zona_id=data.zona_id,
            vendedor_id=data.vendedor_id,
            limite_credito=data.limite_credito,
            dias_credito=data.dias_credito,
        )
        session.add(cli)
        await session.flush()
        return cli

    @staticmethod
    async def listar_clientes(session: AsyncSession, company_id: uuid.UUID) -> Sequence[Cliente]:
        stmt = select(Cliente).where(Cliente.company_id == company_id).order_by(Cliente.nombre)
        res = await session.execute(stmt)
        return res.scalars().all()

    # --- ZONAS Y VENDEDORES ---
    @staticmethod
    async def crear_zona(session: AsyncSession, company_id: uuid.UUID, data: ZonaCreate) -> Zona:
        z = Zona(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
        )
        session.add(z)
        await session.flush()
        return z

    @staticmethod
    async def listar_zonas(session: AsyncSession, company_id: uuid.UUID) -> Sequence[Zona]:
        stmt = select(Zona).where(Zona.company_id == company_id).order_by(Zona.codigo)
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def crear_vendedor(
        session: AsyncSession, company_id: uuid.UUID, data: VendedorCreate
    ) -> Vendedor:
        vend = Vendedor(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
            zona_id=data.zona_id,
            usuario_id=data.usuario_id,
            telefono=data.telefono,
            email=data.email,
            comision_porcentaje=data.comision_porcentaje,
        )
        session.add(vend)
        await session.flush()
        return vend

    @staticmethod
    async def listar_vendedores(session: AsyncSession, company_id: uuid.UUID) -> Sequence[Vendedor]:
        stmt = select(Vendedor).where(Vendedor.company_id == company_id).order_by(Vendedor.codigo)
        res = await session.execute(stmt)
        return res.scalars().all()

    # --- INSTRUMENTOS DE PAGO Y OPERACIONES ---
    @staticmethod
    async def crear_instrumento_pago(
        session: AsyncSession, company_id: uuid.UUID, data: InstrumentoPagoCreate
    ) -> InstrumentoPago:
        inst = InstrumentoPago(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
            tipo=data.tipo.strip().upper(),
            moneda=data.moneda.strip().upper(),
        )
        session.add(inst)
        await session.flush()
        return inst

    @staticmethod
    async def listar_instrumentos_pago(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[InstrumentoPago]:
        stmt = (
            select(InstrumentoPago)
            .where(InstrumentoPago.company_id == company_id)
            .order_by(InstrumentoPago.codigo)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def crear_tipo_operacion(
        session: AsyncSession, company_id: uuid.UUID, data: TipoOperacionCreate
    ) -> TipoOperacion:
        op = TipoOperacion(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
            modulo=data.modulo.strip().upper(),
            afecta_inventario=data.afecta_inventario,
            signo_inventario=data.signo_inventario,
        )
        session.add(op)
        await session.flush()
        return op

    @staticmethod
    async def listar_tipos_operacion(
        session: AsyncSession, company_id: uuid.UUID
    ) -> Sequence[TipoOperacion]:
        stmt = (
            select(TipoOperacion)
            .where(TipoOperacion.company_id == company_id)
            .order_by(TipoOperacion.codigo)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    # --- ALMACENES ---
    @staticmethod
    async def crear_almacen(
        session: AsyncSession, company_id: uuid.UUID, data: WarehouseCreate
    ) -> Warehouse:
        alm = Warehouse(
            company_id=company_id,
            codigo=data.codigo.strip().upper(),
            nombre=data.nombre.strip(),
            activo=True,
        )
        session.add(alm)
        await session.flush()
        return alm

    @staticmethod
    async def listar_almacenes(session: AsyncSession, company_id: uuid.UUID) -> Sequence[Warehouse]:
        stmt = (
            select(Warehouse).where(Warehouse.company_id == company_id).order_by(Warehouse.codigo)
        )
        res = await session.execute(stmt)
        return res.scalars().all()
