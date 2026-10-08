# Galaxy ERP - Registro de Avances del Proyecto

> **Documento de seguimiento de ejecución**  
> Última actualización: 08 de Octubre de 2026  
> Fase actual en progreso: **Fase 1 - Administración** (Fase 0 Completada 100%)

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
- [x] **Ruff** configurado como linter y formateador de código (100% limpio).
- [x] **mypy** configurado con tipado estricto en el núcleo de la aplicación (35 archivos fuente verificados sin errores).
- [x] **pytest** y **pytest-asyncio** configurados con alcance de bucle de eventos consistente para pruebas asíncronas (**20/20 pruebas pasando**).

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
- [x] [seguridad.py](api/app/core/seguridad.py):
  - Hashing seguro de contraseñas con **Argon2id**.
  - Emisión y validación de tokens JWT con claims estrictos (`jti`, `tid`, `cid`, `uid`, `roles`, `iat`, `exp`).
- [x] [main.py](api/app/main.py): Aplicación FastAPI con endpoints de salud operativa `/salud` (liveness), `/salud/lista` (readiness) y router `/api/v1/auth`.

### 1.4 Servidor y Base de Datos (PostgreSQL 18.6)
- [x] PostgreSQL 18.6 verificado y activo en el host.
- [x] Roles de base de datos creados según el principio de mínimo privilegio (Sección 7.4):
  - `erp_owner`: Dueño de las bases, responsable de migraciones y aprovisionamiento DDL.
  - `erp_app`: Rol de ejecución de la API con permisos exclusivamente DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), sin permisos DDL (`CREATE TABLE` denegado y probado).
- [x] Base de datos central del plano de control `erp_control` creada y con permisos configurados.

### 1.5 Plano de Control (`erp_control`)
- [x] [models.py](api/app/control/models.py): Modelos SQLAlchemy declarativos (`Tenant`, `TenantModulo`, `TenantJob`, `PlataformaAdmin`).
- [x] Configuración de Alembic para el control: [alembic_control.ini](api/alembic_control.ini) y [migrations_control/](api/migrations_control/).
- [x] Migración inicial de control: `0001_control_init` aplicada exitosamente sobre `erp_control`.
- [x] [repository.py](api/app/control/repository.py): Operaciones de consulta y mutación asíncronas para tenants y jobs.
- [x] [cli/main.py](api/cli/main.py): CLI `erpctl control init` funcional.

### 1.6 Plano de Datos de Tenants (Bases de Clientes `erp_c_<slug>`)
- [x] Configuración de Alembic para clientes: [alembic.ini](api/alembic.ini) y [migrations/](api/migrations/).
- [x] Modelos base de datos de cliente:
  - [modules/admin/models.py](api/app/modules/admin/models.py): `Company`, `Warehouse`, `AlicuotaIva`, `Correlativo`, `IdempotencyKey`.
  - [modules/identidad/models.py](api/app/modules/identidad/models.py): `Usuario`, `Rol`, `Permiso`, `RolPermiso`, `UsuarioRol`, `SesionRefresh`, `AuditLog`.
- [x] Migración inicial de tenant: `0001_tenant_base` con las 12 tablas principales, claves foráneas y restricciones.
- [x] [aprovisionamiento.py](api/app/control/aprovisionamiento.py): Flujo de **10 pasos de aprovisionamiento automatizado**:
  1. Validación de formato de slug (`^[a-z][a-z0-9-]{1,38}[a-z0-9]$`).
  2. Registro en `erp_control` en estado `aprovisionando` e inicio de `TenantJob`.
  3. Creación de la base de datos `erp_c_<slug>` (dueño `erp_owner`).
  4. Ejecución de migraciones Alembic de tenant hasta `head`.
  5. Configuración de privilegios DML para `erp_app` y tabla `audit_log` estrictamente append-only (sin UPDATE ni DELETE).
  6. Siembra de datos base: permisos del sistema (admin, inventario, ventas, compras, bancos, cxc/cxp, impuestos, reportes) y alícuotas de IVA venezolanas (General 16%, Reducida 8%, Adicional 31%, Exento 0%).
  7. Creación de la primera empresa, depósito inicial `PRINCIPAL`, rol `Administrador` y primer usuario administrador.
  8. Registro de módulos contratados en `tenant_modulo`.
  9. Verificación de conectividad y conteo de tablas con rol `erp_app`.
  10. Transición a estado `activo` y finalización del job en `OK`.
- [x] Comandos de gestión de tenants en `erpctl`:
  - `erpctl tenant crear`: Creación desatendida de clientes.
  - `erpctl tenant listar`: Visualización formateada en tabla con estados e indicador de bases activas (`--solo-db`).
  - `erpctl tenant suspender`: Suspensión inmediata sin pérdida de datos.
  - `erpctl tenant activar`: Reactivación de clientes.

### 1.7 Tenancy, Aislamiento y Autenticación en Runtime
- [x] [tenancy/motores.py](api/app/tenancy/motores.py): Caché LRU de conexiones `AsyncEngine` por cliente con descarte ordenado (`statement_cache_size=0` compatible con PgBouncer).
- [x] [tenancy/registro.py](api/app/tenancy/registro.py): Resolución de metadatos de tenant y validación de estado (`activo` permite paso; `suspendido` emite 403 `TENANT_SUSPENDIDO`; `aprovisionando` emite 503).
- [x] [tenancy/deps.py](api/app/tenancy/deps.py): Dependencia FastAPI `sesion_tenant` que extrae el JWT, valida que el tenant esté activo, abre transacción y ejecuta `SELECT set_config('app.company_id', :cid, true)`.
- [x] [tenancy/rls.py](api/app/tenancy/rls.py): Utilidad para habilitar y forzar Row-Level Security por empresa (Fail-closed).
- [x] [modules/identidad/router.py](api/app/modules/identidad/router.py):
  - `POST /api/v1/auth/login`: Autenticación con slug de cliente + usuario + contraseña (bloqueo por 30 min tras 5 intentos fallidos). Emite access token JWT y refresh token criptográfico.
  - `POST /api/v1/auth/refresh`: Renovación rotativa de tokens (invalida el token anterior y emite uno nuevo).
  - `GET /api/v1/auth/me`: Perfil del usuario autenticado, empresa activa, roles y lista consolidada de permisos.
- [x] [tests/tenancy/test_aislamiento.py](api/tests/tenancy/test_aislamiento.py): Pruebas de integración que garantizan:
  - Flujo completo de login, `/me` y rotación de refresh tokens.
  - Aislamiento estricto: tokens de cliente A rechazados en cliente B.
  - Suspensión de cuenta: tenant suspendido recibe 403 `TENANT_SUSPENDIDO` de inmediato en peticiones de negocio.

### 1.8 Despliegue, Operación y Resiliencia (Cierre de Fase 0)
- [x] Contenedores Quadlet systemd configurados en [deploy/quadlet/](deploy/quadlet/):
  - `redis.container`: Redis 7 alpine con `maxmemory 128mb` y `noeviction`.
  - `api.container`: FastAPI Uvicorn con 2 workers y soporte proxy-headers.
  - `worker.container`: Proceso background para arq/planificador de tareas en segundo plano ([api/app/workers/main.py](api/app/workers/main.py)).
  - `caddy.container`: Caddy 2 con terminación TLS, compresión zstd/gzip y proxy a la API ([deploy/caddy/Caddyfile](deploy/caddy/Caddyfile)).
  - `erp-net.network`: Red interna aislada de Podman.
- [x] Scripts de ciclo de vida de respaldos en [deploy/backup/](deploy/backup/):
  - [respaldo_diario.sh](deploy/backup/respaldo_diario.sh): Respaldo automático de `erp_control` y todas las bases cliente vía `pg_dump -Fc`, cifrado con GPG, retención de 3 días y soporte `rclone`.
  - [restaurar.sh](deploy/backup/restaurar.sh): Desempaquetado/descifrado y restauración atómica probada con `pg_restore`, reaplicación de permisos DML para `erp_app` y auditoría append-only.
- [x] Orquestación de migraciones con `erpctl migrar`:
  - [api/app/control/migraciones.py](api/app/control/migraciones.py): Migración masiva con soporte canario (falla segura que detiene la cola si el canario falla), registro en `tenant_job` y actualización de `schema_rev`.
- [x] Diagnóstico de salud con `erpctl salud`:
  - Inspección en vivo de disco (GB totales/libres y porcentaje), memoria RAM real disponible, conectividad con PostgreSQL y Redis.
- [x] Plantilla segura de variables de entorno [.env.example](.env.example) y [.gitignore](.gitignore) blindado contra fugas de credenciales.

---

## 2. Lo Pendiente por Realizar

### 2.1 Fase 1: Administración (En Progreso)
> **Decisiones Arquitectónicas Definidas por el Usuario:**
> - **Modelo de Despliegue:** SaaS multi-tenant alojado en VPS central.
> - **Retenciones:** Flexibles y configurables por cliente y proveedor (el cliente decide quién retiene IVA/ISLR y quién no).
> - **Almacenamiento:** Sin restricción artificial por volumen de disco.

**Tareas en Desarrollo:**
1. **Modelos y Migraciones del Catálogo de Negocio:**
   - [ ] Empresa (Razón social, RIF, dirección fiscal, teléfono, logo, moneda base, retenciones por defecto).
   - [ ] Depósitos / Almacenes (`Warehouse`).
   - [ ] Categorías de productos (árbol jerárquico).
   - [ ] Catálogo de Productos y Servicios (código, nombre, tipo, unidad de medida, alícuota IVA, costo estándar, precios bimoneda).
   - [ ] Proveedores (RIF, nombre, agente de retención IVA/ISLR sí/no, porcentaje personalizado de retención).
   - [ ] Clientes (Cédula/RIF, nombre, dirección, contribuyente especial sí/no, retención personalizada, lista de precio asignada).
   - [ ] Zonas y Vendedores.
   - [ ] Instrumentos de pago (Efectivo VES/USD, Transferencia, Pago Móvil, Punto de venta, Zelle, etc.).
   - [ ] Tipos de operación y Correlativos de documentos.
2. **Servicio de Monedas y Tasas BCV:**
   - [ ] Modelo `TasaCambio` (moneda origen, moneda destino, tasa con 6 decimales, fecha de vigencia, fuente BCV/manual).
   - [ ] Endpoint y tarea programada para consulta y registro de la tasa oficial del BCV.
3. **Importación Masiva:**
   - [ ] Parser de plantillas Excel (`.xlsx`) con validaciones de tipos, duplicados y reglas de negocio.
4. **API Endpoints & Permisos:**
   - [ ] Routers FastAPI para cada catálogo con auditoría y verificación de permisos por rol.
5. **Frontend Flutter (Kite Shell):**
   - [ ] Estructura base de la aplicación de escritorio y web, autenticación, selector de empresa y pantallas de administración.

---

### 2.2 Fases Siguientes del Roadmap

* **Fase 2: Inventario** (Kardex inmutable, saldos, movimientos atómicos, traslados, ajustes con motivo).
* **Fase 3: Compras y Ventas** (Ciclo de cotizaciones, órdenes, compras, pedidos, facturas, notas de crédito/entrega).
* **Fase 4: Finanzas y Bancos** (Cuentas bancarias, CxC, CxP, aplicación de cobros/pagos bimoneda, conciliación).
* **Fase 5: Impuestos y Reportes Fiscales** (Libros SENIAT, retenciones IVA/ISLR, IGTF, exportación PDF/Excel).
* **Fase 6 & 7: Sincronización y App Móvil de Campo** (Modo offline para vendedores).
* **Fase 8: Piloto, Pruebas de Carga y Endurecimiento Operativo**.
