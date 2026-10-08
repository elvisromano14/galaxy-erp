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
  - Libro de Ventas y Libro de Compras conforme a la normativa tributaria venezolana (período fiscal, RIF, número de factura, número de control, base imponible por alícuota, montos exentos, IVA retenido).
- [x] **Exportación Excel (`app/modules/reportes/exportador.py`):**
  - Generación de archivos `.xlsx` estilizados con cabeceras, totales y formato financiero estándar para presentación ante el SENIAT.
- [x] **Endpoints y Router:** `/api/v1/impuestos/*`.

---

## 3. Pruebas y Verificación

- **Suite de Pruebas Pytest:**
  - `test_ciclo_completo_fases_1_a_5.py`: Simulación end-to-end de un tenant real aprovisionado (carga de catálogos, tasa BCV, compra a proveedor con retención, entrada a inventario, venta a cliente con descuento de stock, cobro por punto de venta/banco, emisión de comprobante de retención y libro fiscal SENIAT).
  - Total: **21 pruebas automatizadas pasando al 100%**.
- **Linter Ruff:** 100% limpio sin errores de estilo ni sintaxis.
- **Mypy:** Tipado estricto verificado en 67 módulos del backend sin fallos.

---

## 4. Próximos Pasos (Roadmap Restante)

* **Fase 6: Sincronización y App Móvil / Frontend Flutter (Kite Shell)**
  - Interfaz de usuario para escritorio y web en Flutter.
  - Modo offline para vendedores de campo con sincronización asíncrona segura.
* **Fase 7: Punto de Venta (POS) y Facturación Rápida**.
* **Fase 8: Piloto, Pruebas de Carga y Endurecimiento Operativo**.
