# Galaxy ERP - Registro de Avances del Proyecto

> **Documento de seguimiento de ejecución**  
> Última actualización: 08 de Octubre de 2026  
> Estado general: **Fases 0 a 5 CULMINADAS al 100% (Backend, Lógica de Dominio, Migraciones y API)**  
> Siguiente hito: **Fase 6 - Sincronización y Frontend Multiplataforma (Flutter / App Móvil)**

---

## 1. Resumen de Fases Completadas

| Fase | Alcance | Estado | Pruebas & Calidad |
| :--- | :--- | :---: | :---: |
| **Fase 0** | Plataforma, Aislamiento, Multi-tenant, Quadlet Podman, Respaldos y CLI `erpctl` | **100%** | 20/20 unit/tenancy |
| **Fase 1** | Catálogos Admin, Monedas, Tasas BCV, Importación Excel, Retenciones Configurables | **100%** | Integrado |
| **Fase 2** | Inventario, Kardex inmutable append-only, Saldos con bloqueo, Ajustes y Traslados | **100%** | Integrado |
| **Fase 3** | Compras y Ventas, Ciclos completos, Correlativos atómicos, Facturación bimoneda | **100%** | Integrado |
| **Fase 4** | Finanzas, Bancos, Cuentas por Cobrar (CxC), Cuentas por Pagar (CxP), Antigüedad | **100%** | Integrado |
| **Fase 5** | Impuestos SENIAT, Comprobantes de Retención IVA/ISLR, Libros Fiscales y Exportador Excel | **100%** | Integrado |
| **Fase 6** | Sincronización Offline, Dispositivos de Preventa, Bloques de Correlativos, Idempotencia | **100%** | Integrado |
| **PDF Fiscal** | Plantillas WeasyPrint/Jinja2 para Facturas de Venta y Comprobantes de Retención | **100%** | Integrado |
| **Frontend** | Shell Multiplataforma Flutter / Dart en `mobile/` (Login, Dashboard, Ventas, Inventario, Sync) | **100%** | Arquitectura |

---

## 2. Detalle de Implementación por Fase

### 2.1 Fase 0: Plataforma, Seguridad y Multi-Tenancy
- [x] Arquitectura SaaS Multi-tenant con aislamiento de base de datos física por cliente (`erp_c_<slug>`).
- [x] Contenedores Quadlet Podman: `redis.container`, `api.container`, `worker.container`, `caddy.container`, `erp-net.network`.
- [x] Reverse proxy Caddy con terminación TLS y compresión zstd/gzip.
- [x] Respaldos en caliente (`pg_dump -Fc` + GPG) y restauración probada (`deploy/backup/`).
- [x] CLI `erpctl` completo: `salud`, `control init`, `tenant crear/listar/suspender/activar`, `migrar`.
- [x] Repositorio público oficial: `https://github.com/elvisromano14/galaxy-erp`.

### 2.2 Fase 1: Administración y Catálogos Base
- [x] **Modelos declarativos SQLAlchemy:**
  - `Company`: RIF, razón social, dirección, teléfono, moneda base, configuración de retenciones.
  - `Warehouse`: Gestión multi-almacén / depósitos.
  - `AlicuotaIva`: Alícuotas fiscales venezolanas (16%, 8%, 31%, 0% exento).
  - `TasaCambio`: Historial de tasas con 6 decimales (`NUMERIC(18,6)`), con integración y scraper BCV asíncrono (`app/modules/admin/bcv.py`).
  - `Categoria`, `Product`: Productos y servicios bimoneda, costos estándar, unidades de medida.
  - `Proveedor`: Soporte para retención configurable individual (el cliente decide quién retiene y el %).
  - `Cliente`: Contribuyente especial, retenciones configurables y listas de precios.
  - `Zona`, `Vendedor`: Estructura comercial.
  - `InstrumentoPago`: Efectivo (VES/USD), Transferencia, Pago Móvil, Punto de venta, Zelle.
  - `Correlativo`: Numeración atómica y segura de documentos por tipo y serie.
- [x] **Importación masiva (`app/modules/admin/importador.py`):**
  - Carga de productos, clientes y proveedores vía plantillas Excel `.xlsx` con validaciones de tipos y duplicados.
- [x] **Endpoints y Router:** `/api/v1/admin/*` con auditoría y roles.

### 2.3 Fase 2: Control de Inventario y Kardex Inmutable
- [x] **Kardex Estricto Append-Only (`stock_movement`):**
  - Privilegios `UPDATE`, `DELETE` y `TRUNCATE` revocados a nivel PostgreSQL para el rol `erp_app`.
  - Trazabilidad total de entradas, salidas, costos unitarios y balances históricos.
- [x] **Saldos Atómicos (`stock_balance`):**
  - Actualización concurrente segura mediante `SELECT ... FOR UPDATE`.
  - Regla de negocio estricta: saldo físico no negativo en salidas de inventario.
- [x] **Ajustes y Traslados:**
  - Modelos y servicios para `AjusteInventario` (con motivos) y `TrasladoInventario` (entre almacenes origen y destino) con impacto atómico en el kardex.
- [x] **Endpoints y Router:** `/api/v1/inventario/*`.

### 2.4 Fase 3: Compras y Ventas
- [x] **Ciclo de Compras (`app/modules/compras/`):**
  - `OrdenCompra` y `CompraFactura`.
  - Validación de alícuotas, cálculo de base imponible, IVA y retenciones configurables del proveedor.
  - Impacto automático: entrada a inventario (Kardex inmutable), creación de Cuenta por Pagar (CxP) y generación de comprobante de retención si aplica.
- [x] **Ciclo de Ventas (`app/modules/ventas/`):**
  - `PresupuestoVenta`, `FacturaVenta`, `FacturaVentaDetalle`, `NotaCreditoVenta`.
  - Asignación atómica de correlativo fiscal por tipo de documento.
  - Descuento automático de inventario físico con verificación de existencia.
  - Generación automática de Cuenta por Cobrar (CxC).
- [x] **Endpoints y Router:** `/api/v1/compras/*` y `/api/v1/ventas/*`.

### 2.5 Fase 4: Finanzas, Bancos y Tesorería
- [x] **Gestión Bancaria (`app/modules/bancos/`):**
  - `CuentaBancaria`: Cuentas en moneda nacional (VES) y extranjera (USD), saldos contables y conciliados.
  - `TransaccionBancaria`: Registro de movimientos (depósitos, retiros, comisiones, transferencias).
- [x] **Cuentas por Cobrar y por Pagar (`app/modules/cxc_cxp/`):**
  - Cobros a clientes (`CobroCliente`) y Pagos a proveedores (`PagoProveedor`) bimoneda.
  - Actualización atómica de saldos de facturas pendientes (estado `pendiente`, `parcial`, `pagada`).
  - Acreditación/Débito automático en las cuentas bancarias asociadas.
  - Reporte de antigüedad de saldos clasificado en períodos: corriente, 1-30 días, 31-60 días, 61-90 días y +90 días.
- [x] **Endpoints y Router:** `/api/v1/bancos/*` y `/api/v1/finanzas/*`.

### 2.6 Fase 5: Impuestos y SENIAT
- [x] **Comprobantes de Retención:**
  - `ComprobanteRetencionIva` y `ComprobanteRetencionIslr` con correlativo fiscal del agente de retención.
- [x] **Libros Fiscales SENIAT:**
  - Libro de Ventas y Libro de Compras conforme a la normativa tributaria venezolana.
- [x] **Exportación Excel y PDF Fiscal:**
  - Reportes `.xlsx` estilizados con cabeceras y fórmulas automáticas ([`exportador.py`](api/app/modules/reportes/exportador.py)).
  - Generador de Factura de Venta y Comprobantes de Retención en PDF vectorial con Jinja2 y WeasyPrint ([`pdf.py`](api/app/modules/reportes/pdf.py)).
- [x] **Endpoints y Router:** `/api/v1/impuestos/*`.

### 2.7 Fase 6: Sincronización Offline y Preventa
- [x] **Modelos (`app/modules/sync/models.py`):**
  - `DispositivoSync`: Registro y autorización de terminales móviles (IMEI / UUID).
  - `SyncBloqueCorrelativo`: Reserva atómica de bloques de números para ventas sin conexión.
  - `SyncOperacionLog`: Auditoría e idempotencia por `client_op_id` con estados `APLICADA`, `RECHAZADA`, `DUPLICADA`.
- [x] **Migración Alembic:** `0003_sincronizacion_offline` aplicada con permisos DML y Row-Level Security por empresa.
- [x] **Endpoints y Router (`app/modules/sync/router.py`):**
  - `POST /api/v1/sync/dispositivos`: Registro de dispositivo móvil.
  - `GET /api/v1/sync/catalogos`: Descarga incremental de productos, clientes, almacenes y existencias con `sync_token`.
  - `POST /api/v1/sync/bloques`: Solicitud de bloque de correlativos offline.
  - `POST /api/v1/sync/operaciones`: Procesamiento transaccional atómico por lotes con savepoints independientes.

### 2.8 Cliente Frontend Multiplataforma (Flutter / Dart)
- [x] Proyecto estructurado en `mobile/`:
  - `mobile/pubspec.yaml` con dependencias Riverpod, Dio y Drift (SQLite).
  - `mobile/lib/core/api_client.dart` con interceptores JWT y multi-tenancy.
  - `mobile/lib/core/theme.dart` con estilo profesional inspirado en Kite.
  - `mobile/lib/features/auth/login_screen.dart` para acceso por cliente (`slug`) + usuario + clave.
  - `mobile/lib/features/dashboard/dashboard_screen.dart` con menú lateral y KPIs.
  - `mobile/lib/features/ventas/ventas_screen.dart` y descarga de facturas en PDF.
  - `mobile/lib/features/inventario/inventario_screen.dart` para existencias y traslados.
  - `mobile/lib/features/sync/sync_screen.dart` para sincronización de campo.

---

## 3. Pruebas y Verificación

- **Suite de Pruebas Pytest:**
  - `test_ciclo_completo_fases_1_a_5.py`: Ciclo de vida completo de compras, inventario, ventas, bancos y libros fiscales.
  - `test_sync_y_pdf.py`: Prueba de integración completa de sincronización móvil offline y descarga de PDF fiscal.
  - Total: **22 pruebas automatizadas pasando al 100%**.
- **Linter Ruff:** 100% limpio sin advertencias ni errores.
- **Mypy:** Tipado estricto verificado en 73 módulos del backend sin fallos.
- **OpenAPI Specification:** 47 endpoints REST documentados en `docs/openapi.json`.

---

## 4. Próximos Pasos (Fase 8: Piloto y Producción)

* **Piloto y Pruebas de Carga (k6 / Locust):** Simulación de estrés con usuarios concurrentes.
* **Compilación de Producción de Flutter:** Generar binarios Web (`flutter build web`) y APK Android para vendedores de campo.
* **Puesta en marcha definitiva con Caddy y Quadlet en el VPS**.
