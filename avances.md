# Galaxy ERP - Registro de Avances del Proyecto

> **Documento de seguimiento de ejecución**  
> Última actualización: 08 de Octubre de 2026  
> Fase actual en progreso: **Fase 0 - Plataforma y Arquitectura Base**

---

## 1. Lo Realizado Hasta Ahora

### 1.1 Repositorio y Entorno de Desarrollo
- [x] Repositorio Git inicializado en rama `main`.
- [x] Entorno virtual Python 3.14 / 3.12 (`.venv`) configurado con todas las dependencias requeridas.
- [x] Archivo [.gitignore](.gitignore) configurado para proteger secretos, entornos virtuales, cachés y volcados.
- [x] Archivo [Makefile](Makefile) con automatización para `install`, `lint`, `format`, `typecheck`, `test` y `run-api`.
- [x] Configuración de dependencias y empaquetado en [api/pyproject.toml](api/pyproject.toml) con Hatchling.
- [x] Contenedor de producción [api/Containerfile](api/Containerfile) multi-etapa con usuario no root `erp` y dependencias de WeasyPrint.

### 1.2 Reglas de Calidad y Verificación Continua
- [x] **Ruff** configurado como linter y formateador de código.
- [x] **mypy** configurado con tipado estricto en el núcleo de la aplicación.
- [x] **pytest** y **pytest-asyncio** configurados con alcance de bucle de eventos consistente para pruebas asíncronas.

### 1.3 Módulos Core de la Aplicación
- [x] [config.py](api/app/core/config.py): Gestión de configuración con Pydantic Settings (URLs de bases de datos, Redis, JWT, zona horaria).
- [x] [tiempo.py](api/app/core/tiempo.py): Gestión centralizada de fechas y horas bajo la zona horaria oficial `America/Caracas` (UTC-4).
- [x] [dinero.py](api/app/core/dinero.py): Reglas monetarias estrictas con `Decimal` (prohibido uso de `float`):
  - Montos contables y documentos: 2 decimales (`NUMERIC(18,2)`).
  - Precios y costos: 4 decimales (`NUMERIC(18,4)`).
  - Cantidades de inventario: 4 decimales (`NUMERIC(18,4)`).
  - Tasas de cambio (BCV / manual): 6 decimales (`NUMERIC(18,6)`).
  - Redondeo `ROUND_HALF_UP`.
- [x] [errores.py](api/app/core/errores.py): Manejador estándar de errores bajo la especificación **RFC 9457 (Problem Details)** con trazabilidad `trace_id`.
- [x] [main.py](api/app/main.py): Aplicación FastAPI con endpoints de salud operativa `/salud` (liveness) y `/salud/lista` (readiness).

### 1.4 Servidor y Base de Datos (PostgreSQL 18.6)
- [x] PostgreSQL 18.6 verificado y activo en el host.
- [x] Roles de base de datos creados según el principio de mínimo privilegio (Sección 7.4):
  - `erp_owner`: Dueño de las bases, responsable de migraciones y aprovisionamiento DDL.
  - `erp_app`: Rol de ejecución de la API con permisos exclusivamente DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), sin permisos DDL (`CREATE TABLE` denegado y probado).
- [x] Base de datos central del plano de control `erp_control` creada y con permisos configurados.

### 1.5 Plano de Control (`erp_control`)
- [x] [models.py](api/app/control/models.py): Modelos SQLAlchemy declarativos:
  - `Tenant`: Registro de clientes con ID `uuidv7`, slug validado por regex, conexión a base `erp_c_<slug>`, estados del ciclo de vida (`aprovisionando`, `activo`, `suspendido`, `archivado`, `fallido`) y revisión de esquema.
  - `TenantModulo`: Módulos licenciados por cliente y fechas de vencimiento.
  - `TenantJob`: Histórico auditable de trabajos de aprovisionamiento, migración y mantenimiento.
  - `PlataformaAdmin`: Administradores del plano de control global.
- [x] Configuración de Alembic para el control: [alembic_control.ini](api/alembic_control.ini) y [migrations_control/](api/migrations_control/).
- [x] Migración inicial de control: `0001_control_init` aplicada exitosamente sobre `erp_control`.
- [x] [repository.py](api/app/control/repository.py): Operaciones de consulta y mutación asíncronas para tenants y jobs.
- [x] [cli/main.py](api/cli/main.py): CLI `erpctl control init` funcional para inicializar y migrar el plano de control.
- [x] Suite de pruebas automatizadas: **14 pruebas pasando** (unitarias e integración real contra PostgreSQL 18).

---

## 2. Lo Pendiente por Realizar

### 2.1 Resto de la Fase 0 (Plataforma y Aislamiento) - *Próximo Bloque*
1. **Cadena de Migraciones de Tenant (`api/migrations/`):**
   - Configuración de Alembic para el plano de datos (`erp_c_<slug>`).
   - Migración inicial con tablas maestras del tenant: `company`, `usuario`, `rol`, `permiso`, `audit_log`, `idempotency_keys`, `correlativo`, `alicuota_iva`, `warehouse`.
2. **Módulo de Identidad (`api/app/modules/identidad/`):**
   - Hashing seguro de contraseñas con **Argon2id**.
   - Emisión y validación de tokens JWT (acceso 15 min, refresh rotativo revocable en BD).
   - Inclusión obligatoria de `tid` (tenant) y `cid` (company) en el JWT.
   - Verificación de permisos por empresa en capa de servicio.
3. **Aprovisionamiento Automatizado (`erpctl tenant crear`):**
   - Implementar los 10 pasos de aprovisionamiento:
     1. Validación de slug.
     2. Registro en `erp_control` en estado `aprovisionando`.
     3. Creación de la base de datos `erp_c_<slug>` (dueño `erp_owner`).
     4. Ejecución de migraciones Alembic de tenant hasta `head`.
     5. Configuración de permisos DML para `erp_app`.
     6. Siembra de datos base (roles Administrador/Contador/Vendedor, monedas VES/USD, alícuotas IVA).
     7. Creación de primera empresa y usuario administrador inicial con enlace de activación temporal.
     8. Asignación de módulos en `tenant_modulo`.
     9. Verificación de conectividad.
     10. Transición a estado `activo`.
   - Comandos de ciclo de vida: `erpctl tenant listar`, `suspender`, `activar`.
4. **Resolución de Tenant y Multitenancy en Runtime (`api/app/tenancy/`):**
   - Registro en memoria / Redis con TTL para lookup de tenants.
   - Caché LRU de motores SQLAlchemy (`AsyncEngine`) por cliente (`motores.py`).
   - Inyección de dependencias `sesion_tenant` con ejecución obligatoria de `SELECT set_config('app.company_id', :cid, true)`.
   - Configuración de políticas **Row-Level Security (RLS)** por empresa en PostgreSQL.
5. **Pruebas de Aislamiento Estricto:**
   - Pruebas que verifiquen que un usuario del cliente A no puede acceder a datos del cliente B bajo ninguna circunstancia.
   - Pruebas que verifiquen que un tenant suspendido recibe 403 `TENANT_SUSPENDIDO`.
6. **Infraestructura y Despliegue Base:**
   - Archivos de servicio Quadlet para Podman (`redis.container`, `api.container`, `worker.container`, `caddy.container`).
   - Configuración de Caddy con TLS y proxy inverso.
   - Script de respaldo por cliente con `pg_dump -Fc` y cifrado GPG.

---

### 2.2 Fases Futuras del Roadmap

* **Fase 1: Administración**
  - CRUD de empresas, depósitos, categorías, productos, proveedores, clientes, zonas, vendedores, instrumentos de pago.
  - Carga de tasas de cambio BCV (manual y automática).
  - Importación masiva de productos desde plantillas Excel.
* **Fase 2: Inventario**
  - Kardex inmutable (`stock_movement`) y saldos (`stock_balance`).
  - Cargos, descargos, traslados entre depósitos y ajustes con motivo obligatorio.
  - Costo estándar, variación de compras, mínimos y máximos, listas de precios.
* **Fase 3: Compras y Ventas**
  - Ciclo de compras: cotización → orden → compra → devolución → notas de entrega.
  - Ciclo de ventas: cotización → presupuesto → pedido → factura → nota de crédito.
  - Integración transaccional con inventario y cuentas por cobrar/pagar.
* **Fase 4: Finanzas y Bancos**
  - Cuentas bancarias, beneficiarios, transacciones.
  - Cuentas por cobrar (CxC) y por pagar (CxP), aplicación de cobros y pagos, antigüedad de saldos.
  - Conciliación bancaria.
* **Fase 5: Impuestos y Reportes Fiscales**
  - Motor tributario venezolano: IVA, retenciones IVA/ISLR, IGTF.
  - Generación de libros de compras y ventas según providencias SENIAT.
  - Motor de reportes declarativo con exportación en PDF, XLSX y CSV.
* **Fase 6 & 7: Sincronización y App Móvil de Campo**
  - *(Pospuesto por solicitud expresa: se abordará en su respectiva fase)*.
* **Fase 8: Piloto, Pruebas de Carga y Endurecimiento Operativo**
  - Pruebas de concurrencia y carga.
  - Simulacros de restauración y recuperación ante desastres.
