# Galaxy ERP: Plan maestro de desarrollo

> **Versión 1.0** · Documento vivo. Cada decisión que cambie la arquitectura se registra en `docs/adr/`.
> Sustituye a las versiones 0.1 y 0.2.

---

## Índice

1. [Visión y alcance](#1-visión-y-alcance)
2. [Glosario](#2-glosario)
3. [Modelo multi-tenant: una base de datos por cliente](#3-modelo-multi-tenant-una-base-de-datos-por-cliente)
4. [Arquitectura general](#4-arquitectura-general)
5. [Servidor, capacidad y presupuestos](#5-servidor-capacidad-y-presupuestos)
6. [Stack tecnológico](#6-stack-tecnológico)
7. [Paso a paso 0: preparar el servidor](#7-paso-a-paso-0-preparar-el-servidor)
8. [Paso a paso 1: plano de control (`erp_control`)](#8-paso-a-paso-1-plano-de-control-erp_control)
9. [Paso a paso 2: resolución de tenant y conexiones](#9-paso-a-paso-2-resolución-de-tenant-y-conexiones)
10. [Paso a paso 3: aprovisionamiento con `erpctl`](#10-paso-a-paso-3-aprovisionamiento-con-erpctl)
11. [Migraciones en todos los clientes](#11-migraciones-en-todos-los-clientes)
12. [Seguridad y aislamiento](#12-seguridad-y-aislamiento)
13. [Estructura del repositorio](#13-estructura-del-repositorio)
14. [Mapa funcional completo](#14-mapa-funcional-completo)
15. [Reglas de negocio transversales](#15-reglas-de-negocio-transversales)
16. [Modelo de datos base](#16-modelo-de-datos-base)
17. [Fiscalidad venezolana](#17-fiscalidad-venezolana)
18. [Sincronización offline](#18-sincronización-offline)
19. [Contrato de la API](#19-contrato-de-la-api)
20. [Experiencia de usuario con Kite](#20-experiencia-de-usuario-con-kite)
21. [Arquitectura del cliente Flutter](#21-arquitectura-del-cliente-flutter)
22. [Despliegue: Podman, Caddy, respaldos](#22-despliegue-podman-caddy-respaldos)
23. [Operación y monitoreo](#23-operación-y-monitoreo)
24. [Calidad, pruebas y CI](#24-calidad-pruebas-y-ci)
25. [Roadmap con tareas por fase](#25-roadmap-con-tareas-por-fase)
26. [Definición de terminado](#26-definición-de-terminado)
27. [Preguntas abiertas](#27-preguntas-abiertas)
28. [Cómo trabajar con Claude en cada fase](#28-cómo-trabajar-con-claude-en-cada-fase)

---

## 1. Visión y alcance

**Galaxy ERP** es un ERP modular para Venezuela que se **vende a varios clientes**. Un solo programa sirve a todos, pero cada cliente tiene su propia base de datos aislada.

Cubre:

- **Administración:** depósitos, categorías, productos, proveedores, clientes, zonas, vendedores, instrumentos de pago, tipos de operación.
- **Inventario:** cargos, descargos, traslados, ajustes, mínimos y máximos, precios manuales y automáticos, impuestos, factor cambiario.
- **Compras:** cotizaciones, órdenes, compras, devoluciones, notas de entrega.
- **Ventas:** cotizaciones, presupuestos, pedidos, facturas, notas de crédito, devoluciones.
- **Bancos:** monedas, cuentas, beneficiarios, transacciones, conciliaciones.
- **Cuentas por cobrar y pagar.**
- **Impuestos:** IVA, retenciones, libros de compras y ventas.
- **Reportes** de proveedores, inventario, vendedores, clientes, ventas, compras e impuestos.
- **App de campo** con venta **sin conexión** para vendedores.

**Principios del producto**

1. **Intuitivo:** lo frecuente a dos toques, lenguaje del usuario, errores que dicen qué hacer.
2. **Escalable:** se añaden clientes con un comando; se mueven a otro servidor cambiando una fila.
3. **Auditable:** nada financiero se borra; todo se anula con movimientos compensatorios.
4. **Un solo código:** nunca se bifurca el programa por cliente.

---

## 2. Glosario

| Término | Definición |
|---|---|
| **Plataforma** | El software y la infraestructura que operas tú |
| **Cliente / tenant** | Organización que contrata Galaxy ERP. Tiene **su propia base de datos** |
| **Empresa (company)** | Razón social con RIF dentro de un cliente. Un cliente puede tener varias |
| **Plano de control** | Base `erp_control`: registro de clientes, módulos y estados. Sin datos de negocio |
| **Plano de datos** | Las bases de cada cliente (`erp_c_<slug>`) |
| **Módulo** | Agrupación funcional licenciable (`ventas`, `bancos`, …) |
| **Aprovisionamiento** | Crear y dejar lista la base de un cliente nuevo |
| **Canario** | Cliente de prueba que recibe primero cada migración |

---

## 3. Modelo multi-tenant: una base de datos por cliente

### 3.1 Qué significa

Un **mismo programa** (misma API, misma versión) atiende a **muchos clientes**. Cada cliente tiene **su propia base de datos PostgreSQL**, completamente separada de las demás. Todas viven en el mismo servidor PostgreSQL mientras la capacidad lo permita.

```
VPS (PostgreSQL 18)
├── erp_control          → registro: qué clientes existen y dónde vive su base
├── erp_c_acme           → Acme C.A.       (sus datos, usuarios y empresas)
├── erp_c_distnorte      → Distribuidora Norte (datos totalmente separados)
└── erp_c_xyz            → XYZ             (datos totalmente separados)
```

- **1 cliente = 1 base de datos.**
- **1 empresa (RIF) = 1 `company_id` dentro de la base del cliente.**
- Una base por cliente **no** significa un servidor por cliente.

### 3.2 Cómo entra un usuario

1. Escribe **código de cliente** (`acme`), usuario y contraseña.
2. La API consulta `erp_control` y encuentra que `acme` vive en `erp_c_acme`.
3. Emite un JWT con `tid` (cliente) y `cid` (empresa activa).
4. Toda consulta posterior va solo a `erp_c_acme`. La conexión la decide el registro, **nunca** lo que envíe el usuario.

### 3.3 Reglas inquebrantables

1. Ningún dato de negocio vive en `erp_control`.
2. Ninguna consulta cruza bases de clientes distintos.
3. `tenant_id` y `company_id` salen del token, jamás del cuerpo de la petición.
4. Cada cliente se respalda, exporta, restaura y elimina de forma independiente.
5. Cada cliente se puede mover a otro servidor cambiando su fila en `erp_control`.
6. Un solo código y una sola cadena de migraciones para todos.

### 3.4 Qué ganas y qué pagas

| Ventaja | Costo |
|---|---|
| Aislamiento real; un fallo no contagia a otros clientes | Cada base tiene su copia de las tablas |
| Entregas al cliente su base con un `pg_dump` | Migraciones una vez por cliente (lo automatiza `erpctl`) |
| Respaldo y restauración por cliente | Más conexiones (se resuelve con PgBouncer) |
| Mover un cliente = cambiar una fila | Más RAM y disco que un esquema compartido |
| Eliminar un cliente = borrar una base | Exige automatización desde el día uno |

### 3.5 Alternativas descartadas

| Modelo | Motivo |
|---|---|
| `company_id` en una sola base para todos | Aislamiento solo lógico; un error de código expone datos ajenos |
| Un esquema por cliente en una base | Migraciones repetidas dentro de la misma base, `pg_dump` mezcla clientes |

---

## 4. Arquitectura general

```
               Tailscale (red privada)
                        │
                 ┌──────▼──────┐
                 │    Caddy    │  TLS, web Flutter, proxy /api
                 └──────┬──────┘
                        │
                 ┌──────▼──────┐        ┌──────────┐
                 │ API FastAPI │───────►│  Redis   │  caché, locks, colas
                 │ (monolito   │        └──────────┘
                 │  modular)   │               ▲
                 └──────┬──────┘        ┌──────┴──────┐
                        │               │ Worker +    │
                        │               │ planificador│
                        │               └─────────────┘
                 ┌──────▼──────┐
                 │  PgBouncer  │  modo transaction
                 └──────┬──────┘
          ┌─────────────┼──────────────┐
   ┌──────▼─────┐ ┌─────▼──────┐ ┌─────▼──────┐
   │ erp_c_acme │ │erp_c_norte │ │ erp_c_xyz  │  plano de datos
   └────────────┘ └────────────┘ └────────────┘
                 ┌─────────────┐
                 │ erp_control │  plano de control
                 └─────────────┘
```

**Decisiones**

1. **Monolito modular** en Python. Una venta descuenta inventario, crea la CxC y calcula impuestos en una sola transacción; eso es más simple y seguro en un solo proceso.
2. **PostgreSQL es la fuente de verdad.** Redis solo guarda datos reconstruibles.
3. **Movimientos inmutables** (kardex) para inventario, bancos y CxC/CxP.
4. **Dinero con `NUMERIC` y `Decimal`.** Nunca `float`.
5. **Offline en el cliente, validación final en el servidor.**
6. **Sin microservicios ni Kubernetes.** Se evalúan solo si el volumen lo exige.

---

## 5. Servidor, capacidad y presupuestos

### 5.1 Servidor

- vpsdime, Ubuntu Server 24.04, 2 vCPU, 4 GB RAM, 20 GB SSD.
- PostgreSQL 18 en el host. Podman para el resto. Tailscale para el acceso.
- Acceso solo por Tailscale; SSH también restringido a la tailnet.

### 5.2 Presupuesto de memoria

| Componente | Objetivo |
|---|---|
| SO + Tailscale | ~600 MB |
| PostgreSQL 18 (host) | ~1,0 GB |
| PgBouncer | ~20 MB |
| API (Uvicorn, 2 workers) | ~700 MB |
| Worker + planificador | ~400 MB |
| Redis (`maxmemory 128mb`) | ~150 MB |
| Caddy | ~50 MB |
| **Margen** | ~1,0 GB |

### 5.3 Presupuesto de disco (el límite real)

20 GB es poco. Mide desde el piloto:

| Concepto | Medición | Acción |
|---|---|---|
| Tamaño por cliente | `pg_database_size()` | Registrar semanalmente |
| Crecimiento mensual | Comparar mediciones | Proyectar saturación |
| `pg_wal` | Tamaño del directorio | Ajustar `max_wal_size` |
| Respaldos locales | `/var/backups/erp` | Retención local 3 a 7 días |
| Logs | `journalctl --disk-usage` | `SystemMaxUse=500M` |
| Imágenes Podman | `podman system df` | `podman image prune` programado |

**Regla de capacidad:** con disco > 75 % o margen de RAM < 500 MB en uso normal, **no vendas más clientes en ese servidor**; contrata un segundo VPS y mueve clientes. Considera ampliar disco antes de vender el segundo cliente; 20 GB se agotan rápido con respaldos locales, WAL e imágenes.

---

## 6. Stack tecnológico

| Área | Tecnología | Ejecución |
|---|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 | Contenedor `api` |
| ORM | SQLAlchemy 2.x async + asyncpg | Librería |
| Migraciones | Alembic (cadena única, orquestada por `erpctl`) | Comando |
| Pool | PgBouncer, modo `transaction` | Host o contenedor |
| Caché y colas | Redis 7 | Contenedor |
| Tareas | arq + APScheduler (planificador en un solo proceso) | Contenedor `worker` |
| PDF | WeasyPrint (plantillas HTML/CSS) | `api`, `worker` |
| Exportación | openpyxl, CSV | Librería |
| Auth | JWT 15 min + refresh rotativo en BD + Argon2id | Librería |
| Proxy/TLS | Caddy 2 con certificado de Tailscale | Contenedor |
| CLI | Typer (`erpctl`) | Contenedor `api` |
| Logs | structlog JSON a stdout → journald | Host |
| Respaldos | `pg_dump -Fc` por cliente + GPG + rclone | systemd timer |
| Cliente | Flutter 3.x / Dart 3.x | Build independiente |
| UI | **Kite Flutter Admin Dashboard** como base visual | `mobile/` |
| Estado | Riverpod | Librería |
| HTTP | Dio + cliente generado de OpenAPI (`dart-dio`) | Build |
| Local | Drift (SQLite) | Dispositivo |
| Pruebas | pytest, httpx, testcontainers (PostgreSQL 18) | CI |
| Calidad | Ruff, mypy estricto en `core`, `inventario`, `ventas`, `bancos` | CI |

**Sobre Kite** (https://github.com/ColorlibHQ/kite-flutter-admin-dashboard):

- **Verifica la licencia en el repositorio** antes de comercializar: uso comercial, redistribución y avisos obligatorios.
- Cópialo a `mobile/` y versiónalo con tu código; no lo dejes como dependencia externa.
- Elimina pantallas demo y datos simulados desde el primer día.
- Actualiza dependencias a tu versión de Flutter antes de integrarlo.
- Reutiliza: shell con menú lateral, tarjetas de indicadores, tablas, gráficas, formularios. Crea propio lo específico del ERP.

---

## 7. Paso a paso 0: preparar el servidor

> Ejecuta cada bloque y valida con su **Verificación** antes de seguir.

### 7.1 Sistema base

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y podman uidmap passt gnupg rclone ufw jq curl
sudo timedatectl set-timezone America/Caracas
```

**Verificación:** `podman --version` y `timedatectl` muestran la zona correcta.

### 7.2 Usuario de servicio rootless

```bash
sudo useradd -m -s /bin/bash erp
sudo loginctl enable-linger erp
sudo -iu erp podman run --rm docker.io/library/hello-world
```

**Verificación:** el contenedor imprime el mensaje de bienvenida. No ejecutes Podman como root.

### 7.3 Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0
sudo ufw enable
```

**Verificación:** `sudo ufw status verbose`. Desde internet público no debe responder ningún puerto. Si quieres SSH público de respaldo, ábrelo solo con límite de intentos (`ufw limit 22/tcp`); lo recomendable es SSH solo por Tailscale.

### 7.4 PostgreSQL 18

`/etc/postgresql/18/main/postgresql.conf`:

```conf
listen_addresses = 'localhost'
max_connections = 40
shared_buffers = 256MB
work_mem = 8MB
maintenance_work_mem = 128MB
effective_cache_size = 1GB
wal_compression = on
max_wal_size = 1GB
log_min_duration_statement = 500
password_encryption = scram-sha-256
```

Roles (como `postgres`):

```sql
CREATE ROLE erp_owner LOGIN PASSWORD '***' CREATEDB;   -- dueño de bases, migraciones y aprovisionamiento
CREATE ROLE erp_app   LOGIN PASSWORD '***';            -- usa la API, sin DDL
CREATE DATABASE erp_control OWNER erp_owner;
REVOKE CONNECT ON DATABASE erp_control FROM PUBLIC;
GRANT  CONNECT ON DATABASE erp_control TO erp_app;
```

`pg_hba.conf` (solo lo necesario):

```conf
local  all  postgres                       peer
host   all  erp_owner  127.0.0.1/32        scram-sha-256
host   all  erp_app    127.0.0.1/32        scram-sha-256
```

**Verificación:** `psql -h 127.0.0.1 -U erp_app erp_control -c "select 1"` responde; `erp_app` **no** puede hacer `CREATE TABLE`.

### 7.5 PgBouncer (recomendado en el host)

```bash
sudo apt install -y pgbouncer
```

`/etc/pgbouncer/pgbouncer.ini`:

```ini
[databases]
* = host=127.0.0.1 port=5432

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 200
default_pool_size = 5
reserve_pool_size = 2
server_idle_timeout = 300
```

**Verificación:** `psql -h 127.0.0.1 -p 6432 -U erp_app erp_control -c "select 1"`.

> Los contenedores alcanzan el host mediante `host.containers.internal`. Con redes `pasta` rootless puede requerir `--map-gw`. Comprueba la conectividad desde un contenedor de prueba **antes** de continuar: `podman run --rm --network pasta:--map-gw docker.io/library/postgres:18 pg_isready -h host.containers.internal -p 6432`. Si prefieres simplicidad, usa `Network=host` para `api` y `worker` (el firewall ya limita el acceso a Tailscale).

### 7.5.1 Plan B si no se usa PgBouncer en el host

Ejecutarlo en contenedor con la misma configuración y exponer solo a la red interna de Podman. Documenta la elección en un ADR.

### 7.6 Tailscale y certificado

```bash
tailscale status
sudo tailscale cert galaxy-erp.<tu-tailnet>.ts.net
```

Copia el certificado y la clave a `/home/erp/erp/deploy/certs/` con permisos `600` propiedad de `erp`. Programa su renovación (cada 60 a 80 días).

### 7.7 Límites de logs y disco

`/etc/systemd/journald.conf.d/erp.conf`:

```conf
[Journal]
SystemMaxUse=500M
```

**Verificación:** `journalctl --disk-usage`.

### 7.8 Checklist final del paso 0

- [ ] Podman rootless funciona con el usuario `erp`
- [ ] PostgreSQL 18 solo en localhost
- [ ] `erp_owner` y `erp_app` creados; `erp_app` sin DDL
- [ ] PgBouncer responde en 6432
- [ ] `erp_control` creada
- [ ] Certificado Tailscale emitido
- [ ] `ufw` activo solo para tailscale0
- [ ] journald limitado

---

## 8. Paso a paso 1: plano de control (`erp_control`)

Base pequeña con su propia migración Alembic (`api/migrations_control/`).

```sql
CREATE TABLE tenant (
    id          uuid PRIMARY KEY DEFAULT uuidv7(),
    slug        varchar(40)  NOT NULL UNIQUE CHECK (slug ~ '^[a-z][a-z0-9-]{1,38}[a-z0-9]$'),
    nombre      varchar(200) NOT NULL,
    db_host     varchar(120) NOT NULL DEFAULT '127.0.0.1',
    db_port     integer      NOT NULL DEFAULT 6432,         -- PgBouncer
    db_name     varchar(63)  NOT NULL UNIQUE,               -- erp_c_<slug>
    estado      varchar(20)  NOT NULL CHECK (estado IN
                  ('aprovisionando','activo','suspendido','archivado','fallido')),
    plan        varchar(40)  NOT NULL,
    es_canario  boolean      NOT NULL DEFAULT false,
    schema_rev  varchar(64),                                -- última revisión Alembic aplicada
    creado_en   timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE tenant_modulo (
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    modulo      varchar(40) NOT NULL,
    habilitado  boolean NOT NULL DEFAULT true,
    vence_en    date,
    PRIMARY KEY (tenant_id, modulo)
);

CREATE TABLE tenant_job (
    id           uuid PRIMARY KEY DEFAULT uuidv7(),
    tenant_id    uuid REFERENCES tenant(id),
    tipo         varchar(30) NOT NULL,   -- CREAR, MIGRAR, EXPORTAR, MOVER, ARCHIVAR, RESTAURAR_PRUEBA
    estado       varchar(20) NOT NULL,   -- EN_CURSO, OK, ERROR
    detalle      jsonb,
    iniciado_en  timestamptz NOT NULL DEFAULT now(),
    terminado_en timestamptz
);

CREATE TABLE plataforma_admin (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    email         varchar(200) NOT NULL UNIQUE,
    password_hash text NOT NULL,         -- Argon2id
    activo        boolean NOT NULL DEFAULT true
);
```

Notas:

- `uuidv7()` existe en PostgreSQL 18 y da mejor localidad de índice que UUID aleatorios.
- `plataforma_admin` es distinto de los usuarios de cada cliente; solo para la consola de operación.
- Respaldo diario de `erp_control`; es pequeña.

**Verificación:** `erpctl control init` aplica la migración y `\dt` muestra las cuatro tablas.

---

## 9. Paso a paso 2: resolución de tenant y conexiones

### 9.1 Flujo de una petición

1. Caddy recibe y reenvía a la API.
2. La API valida el JWT y lee `tid` y `cid`.
3. Consulta el registro del tenant en Redis (`t:reg:{tid}`, TTL 5 min); si no existe, lee `erp_control`.
4. Verifica `estado` (si no es `activo`, responde 403/410/503 según el caso) y módulo habilitado.
5. Obtiene el motor del tenant de una caché LRU.
6. Abre transacción y ejecuta `SET LOCAL app.company_id = '<cid>'`.
7. Los logs incluyen `tenant_id`, `company_id`, `usuario_id`, `trace_id`.

### 9.2 Caché de motores

```python
# app/tenancy/motores.py (esquema)
from collections import OrderedDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

class MotoresDeClientes:
    def __init__(self, maximo: int = 20):
        self._cache: OrderedDict[str, AsyncEngine] = OrderedDict()
        self._max = maximo

    async def obtener(self, t) -> AsyncEngine:
        if t.id in self._cache:
            self._cache.move_to_end(t.id)
            return self._cache[t.id]
        motor = create_async_engine(
            t.url_app(),                      # apunta a PgBouncer, rol erp_app
            pool_size=3, max_overflow=2, pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},   # requerido con PgBouncer transaction
        )
        self._cache[t.id] = motor
        if len(self._cache) > self._max:
            _, viejo = self._cache.popitem(last=False)
            await viejo.dispose()
        return motor
```

Con 20 motores × 5 conexiones potenciales, PgBouncer concentra todo en pocas conexiones reales al servidor.

### 9.3 Dependencia de sesión por petición

```python
# app/tenancy/deps.py (esquema)
async def sesion_tenant(ctx: ContextoAuth = Depends(contexto_auth)):
    registro = await registro_tenant(ctx.tid)          # Redis → erp_control
    exigir_activo(registro)
    motor = await motores.obtener(registro)
    async with AsyncSession(motor) as s, s.begin():
        await s.execute(text("SELECT set_config('app.company_id', :c, true)"), {"c": str(ctx.cid)})
        yield s
```

`set_config(..., true)` equivale a `SET LOCAL` y se limpia al terminar la transacción.

### 9.4 Pruebas obligatorias de este paso

- Un token del cliente A no llega a datos del cliente B aunque se altere `tid`.
- Un tenant suspendido recibe 403 `TENANT_SUSPENDIDO`.
- Un tenant `aprovisionando` recibe 503.
- Se reutiliza el motor entre peticiones y se libera al exceder el máximo.

---

## 10. Paso a paso 3: aprovisionamiento con `erpctl`

### 10.1 Comando

```bash
erpctl tenant crear --slug acme --nombre "Acme C.A." --plan pro \
    --modulos ventas,inventario,compras --admin-email admin@acme.com
```

### 10.2 Pasos internos (cada uno registrado en `tenant_job`)

1. **Validar** el slug y que no exista.
2. **Registrar** el tenant en `erp_control` con estado `aprovisionando`.
3. **Crear la base:**
   ```sql
   CREATE DATABASE erp_c_acme OWNER erp_owner;
   REVOKE CONNECT ON DATABASE erp_c_acme FROM PUBLIC;
   GRANT  CONNECT ON DATABASE erp_c_acme TO erp_app;
   ```
4. **Migrar** hasta `head` con conexión directa (puerto 5432, `erp_owner`, nunca por PgBouncer).
5. **Permisos del rol de aplicación** (en la nueva base):
   ```sql
   GRANT USAGE ON SCHEMA public TO erp_app;
   ALTER DEFAULT PRIVILEGES FOR ROLE erp_owner IN SCHEMA public
       GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO erp_app;
   ALTER DEFAULT PRIVILEGES FOR ROLE erp_owner IN SCHEMA public
       GRANT USAGE, SELECT ON SEQUENCES TO erp_app;
   ```
   Las tablas de auditoría y kardex solo reciben `SELECT, INSERT` para `erp_app`.
6. **Sembrar datos base:** permisos del sistema, roles predefinidos (Administrador, Contador, Vendedor, Depósito, Solo lectura), monedas VES y USD, alícuotas de IVA vigentes, conceptos de retención.
7. **Crear la primera empresa y el primer administrador** con enlace de activación de un solo uso, válido 24 h. La contraseña nunca pasa por línea de comandos ni logs.
8. **Habilitar módulos** en `tenant_modulo` según el plan.
9. **Verificar:** conexión por PgBouncer con `erp_app`, conteo de tablas esperadas, revisión de esquema.
10. **Activar:** estado `activo` y limpiar la caché del registro en Redis.

Si falla un paso: estado `fallido`, detalle en `tenant_job`, **no se borra la base automáticamente**. Borrar exige `erpctl tenant eliminar --slug X --confirmar X`.

### 10.3 Ciclo de vida

| Estado | Significado | La API responde |
|---|---|---|
| `aprovisionando` | Creando | 503 |
| `activo` | Operación normal | Normal |
| `suspendido` | Falta de pago o decisión comercial | 403 `TENANT_SUSPENDIDO` (sin pérdida de datos) |
| `archivado` | Exportado y retirado | 410 |
| `fallido` | Error al aprovisionar | 503 + alerta al operador |

### 10.4 Otros comandos de `erpctl`

| Comando | Acción |
|---|---|
| `tenant listar` | Clientes, estado, tamaño, revisión |
| `tenant suspender / activar` | Cambia estado e invalida caché |
| `tenant exportar --slug X` | `pg_dump -Fc` cifrado: entrega al cliente su base completa |
| `tenant mover --slug X --a vps2` | Exporta, restaura en destino, valida conteos, cambia `db_host`; origen queda en solo lectura 7 días |
| `tenant archivar --slug X` | Exporta, verifica y retira |
| `migrar --todos \| --slug X` | Ver sección 11 |
| `respaldar --todos \| --slug X` | Respaldo cifrado |
| `salud` | Disco, RAM, conexiones, tamaños por cliente |

---

## 11. Migraciones en todos los clientes

**Principios**

- Una sola cadena Alembic para todos los clientes.
- `erp_control.tenant.schema_rev` guarda la revisión de cada uno.
- Reversibles y probadas con `upgrade` y `downgrade` en CI.
- Una falla en un cliente **no detiene** a los demás; se registra y se reintenta.

**Orquestación** (`erpctl migrar --todos`)

1. Listar tenants `activo` y `suspendido`.
2. Migrar primero el **canario**; si falla, detener todo.
3. Migrar el resto, uno a uno, con conexión directa del dueño.
4. Registrar en `tenant_job` y actualizar `schema_rev`.
5. Reporte final: migrados, fallidos, omitidos.

**Reglas para escribir migraciones**

- No borrar columnas en la misma versión en que se dejan de usar: primero dejar de usarlas, luego borrar en una versión posterior (patrón expandir y contraer).
- Cambios masivos de datos en un job del `worker`, no dentro de la migración.
- Índices sobre tablas grandes con `CREATE INDEX CONCURRENTLY` fuera de transacción.
- Toda migración nueva con prueba de `downgrade`.
- La API debe tolerar el esquema de la revisión anterior durante el despliegue.

---

## 12. Seguridad y aislamiento

| Capa | Mecanismo |
|---|---|
| Red | Solo Tailscale; PostgreSQL y PgBouncer solo en localhost |
| Base | `erp_app` sin DDL; `erp_owner` solo para migraciones y aprovisionamiento |
| Cliente | Base separada; `REVOKE CONNECT FROM PUBLIC` |
| Empresa | `company_id` en todas las tablas de negocio + Row-Level Security |
| Aplicación | Permisos verificados en el servicio, no solo en el router |
| Autenticación | Argon2id, bloqueo tras intentos fallidos, refresh rotativo revocable |
| Auditoría | `audit_log` append-only por cliente |

### 12.1 Row-Level Security

```sql
ALTER TABLE producto ENABLE ROW LEVEL SECURITY;
ALTER TABLE producto FORCE ROW LEVEL SECURITY;
CREATE POLICY por_empresa ON producto
    USING      (company_id = current_setting('app.company_id', true)::uuid)
    WITH CHECK (company_id = current_setting('app.company_id', true)::uuid);
```

Si `app.company_id` no está definido, las consultas devuelven cero filas: falla cerrado.

### 12.2 Pruebas obligatorias en CI

- Aislamiento entre clientes y entre empresas del mismo cliente.
- `erp_app` no puede ejecutar `CREATE`, `DROP` ni `ALTER`.
- `erp_app` no puede `UPDATE` ni `DELETE` en `stock_movement` ni `audit_log`.
- Un tenant suspendido recibe 403 en todo endpoint de negocio.

### 12.3 Autenticación y permisos

- Inicio de sesión: **código de cliente + usuario + contraseña**.
- JWT de acceso (15 min) con `tid`, `cid`, `uid`, `roles`. Refresh rotativo guardado en BD, revocable.
- Roles por empresa; los roles agrupan permisos como `ventas.pedido.crear`, `inventario.ajuste.aprobar`.
- Permisos sensibles separados: anular, cambiar precios, impuestos o tasas, ver costos, ver márgenes.
- Los vendedores ven solo sus clientes y ventas, filtrado en el servicio.
- Rotación de la clave JWT con convivencia de dos claves.

### 12.4 Secretos

- Archivos `.env` con permisos `600`, propiedad de `erp`, fuera del repositorio.
- Clave GPG privada de respaldos fuera del VPS.
- Contraseñas únicas por rol; cambiar las de ejemplo al instalar.

---

## 13. Estructura del repositorio

```
galaxy-erp/
├── api/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, db, redis, seguridad, errores, dinero, tiempo
│   │   ├── control/           # acceso a erp_control (capa más baja)
│   │   ├── tenancy/           # registro, motores, dependencias, RLS
│   │   ├── modules/
│   │   │   ├── identidad/     # usuarios, roles, permisos, sesiones, auditoría
│   │   │   ├── admin/         # empresas, depósitos, categorías, productos, clientes,
│   │   │   │                  # proveedores, vendedores, zonas, monedas, tasas, instrumentos
│   │   │   ├── inventario/
│   │   │   ├── compras/
│   │   │   ├── ventas/
│   │   │   ├── bancos/
│   │   │   ├── cxc_cxp/
│   │   │   ├── impuestos/     # motor fiscal, libros, emisión
│   │   │   ├── sincronizacion/
│   │   │   └── reportes/      # definiciones declarativas sobre vistas
│   │   └── workers/
│   ├── migrations/            # Alembic de tenants (cadena única)
│   ├── migrations_control/    # Alembic de erp_control
│   ├── cli/                   # erpctl
│   ├── tests/
│   │   ├── unit/ integration/ tenancy/ fiscal/ propiedades/ sync/
│   ├── pyproject.toml
│   └── Containerfile
├── mobile/                    # Flutter (base Kite)
│   └── lib/{core,data,domain,features}/
├── deploy/
│   ├── quadlet/  caddy/  pgbouncer/  env/  backup/  scripts/
├── docs/
│   ├── adr/  fiscal/  ux/  openapi.json
├── Makefile
└── README.md
```

**Reglas de dependencia**

- Un módulo llama a los **servicios** de otro, nunca a sus tablas.
- `ventas` llama a `inventario.services.registrar_descargo(...)`; no escribe en el kardex.
- `reportes` solo lee vistas y no contiene lógica.
- `impuestos` es la única fuente de cálculo de IVA y retenciones.
- `control` no importa nada de `modules`.
- Estructura interna de cada módulo: `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`, `permisos.py`.

---

## 14. Mapa funcional completo

### 14.1 Administración (Fase 1)

| Entidad | Notas |
|---|---|
| Empresas | RIF, razón social, tipo de contribuyente, correlativos |
| Depósitos | Almacenes con responsable |
| **Categorías** (antes "instancias") | Jerárquicas si se requiere |
| Productos | Código, barras, unidad, costo estándar, alícuota, categoría, mínimo y máximo |
| Proveedores | RIF, contribuyente, condiciones de pago |
| Clientes | RIF, contribuyente, zona, vendedor, límite de crédito |
| Zonas | Agrupación geográfica |
| Vendedores | Usuario vinculado, zona, comisión |
| Instrumentos de pago | Efectivo, transferencia, pago móvil, punto de venta, etc. |
| Tipos de operación | Catálogo de operaciones del sistema |
| Monedas y tasas | VES, USD, BCV por fecha |

### 14.2 Inventario (Fase 2)

Cargos, descargos, traslados (dos movimientos atómicos), ajustes (motivo obligatorio), cálculo de mínimos y máximos (propone, no aplica sin aprobación), ajuste de precios manual (con vigencia y aprobación), ajuste de precios automático (regla programada), ajuste de impuestos (Fase 5), factor cambiario (Fase 1).

### 14.3 Compras (Fase 3)

Cotizaciones → Órdenes de compra → Compras (recepción). Anulación de órdenes. Devoluciones de compra. Notas de entrega y devolución de notas de entrega.

### 14.4 Ventas (Fase 3)

Cotizaciones → Presupuestos → Pedidos → Facturas → Notas de crédito. Anulación de presupuestos. Devolución de pedidos.

### 14.5 Bancos y finanzas (Fase 4)

Cuentas, bancos, beneficiarios, transacciones, operaciones, conciliaciones, CxC y CxP bancarias, aplicación de pagos y antigüedad de saldos.

### 14.6 Reportes (Fases 2 a 5)

| Grupo | Reportes |
|---|---|
| Proveedores | Listado, análisis, estadísticas, estado de cuenta, CxP, análisis de vencimiento, relación de pagos, transacciones pendientes, compras de productos |
| Categorías | Inventario por categoría, consolidado, estadística |
| Inventario | Productos, reposición, análisis compra-venta, lista de precios, inventario físico, análisis de productos |
| Vendedores | Listado, comisiones, efectividad, última venta a clientes, ventas por categoría y por producto, estadísticas |
| Clientes | Listado, análisis, estadísticas, estado de cuenta, CxC, vencimientos, relación de cobros, recibos y pagos adelantados, retención de impuestos, ventas de productos |
| Ventas | Transacciones, cierre diario, relación de ventas, cierre de caja, transacciones procesadas, ventas a crédito, ventas por categoría |
| Compras | Compras, compras por categoría |
| Impuestos | IVA cobrado, libro de ventas, IVA pagado, libro de compras, retención de IVA |

Cada reporte es una **definición declarativa**: vista SQL, filtros permitidos, columnas, formato y exportación (PDF, XLSX, CSV). Un reporte nuevo no requiere código nuevo de motor.

### 14.7 Nombres en la interfaz

| Término original | En la UI |
|---|---|
| Instancias | **Categorías** |
| Operaciones (catálogo) | **Tipos de operación** |
| Factor cambiario | **Tasa de cambio** |

---

## 15. Reglas de negocio transversales

### 15.1 Movimientos inmutables

- Inventario, bancos y CxC/CxP se registran como movimientos.
- Los saldos se actualizan en la **misma transacción** que el movimiento.
- Anular genera un movimiento compensatorio. Nunca `DELETE` en documentos aprobados.
- Prueba de propiedad obligatoria: saldo = suma del kardex.

### 15.2 Estados de documentos

```
borrador ──► aprobado ──► anulado
```

- Solo `aprobado` afecta inventario, saldos, libros.
- Un aprobado no se edita: se corrige con nota de crédito/débito o se anula con motivo.
- Anular exige permiso y motivo.

### 15.3 Dinero, cantidades y tasas

| Dato | Tipo |
|---|---|
| Montos de documento | `NUMERIC(18,2)` |
| Precios y costos | `NUMERIC(18,4)` |
| Cantidades | `NUMERIC(18,4)` |
| Tasa de cambio | `NUMERIC(18,6)` con fecha y fuente (`BCV`, `MANUAL`) |

- `Decimal` en Python; nunca `float`.
- Redondeo centralizado en `core/dinero.py` y decidido en un ADR.
- Cada documento guarda sus montos en VES y USD **con la tasa usada**. Un documento histórico nunca se recalcula.

### 15.4 Costeo estándar

- Cada producto tiene `costo_estandar` con vigencia.
- Diferencia entre costo real de compra y estándar = **variación de costo**, registrada aparte.
- Cambiar el estándar no recalcula movimientos históricos.
- Cambiar el estándar exige permiso y queda en auditoría. Si se revalúa el inventario existente se genera un ajuste explícito.

### 15.5 Precios

- Vigencia (`valido_desde`, `valido_hasta`) y origen (`MANUAL`, `AUTOMATICO`).
- Ajuste automático = regla aprobada que el planificador aplica en su fecha.
- Listas por cliente, zona o vendedor: pendiente de decisión (sección 27).

### 15.6 Numeración

- Correlativos por empresa y tipo de documento, **sin huecos** en documentos fiscales.
- Se asignan al aprobar, con bloqueo de fila en la tabla `correlativo`.
- Los bloques por dispositivo para offline están en la sección 18.

### 15.7 Concurrencia

- Descargo de inventario: `SELECT ... FOR UPDATE` sobre `stock_balance`.
- Entidades editables: control optimista con `version`; conflicto = 409.
- Redis para locks de procesos largos (cierre diario), no para proteger filas.

### 15.8 Idempotencia

- Toda escritura desde cliente acepta `Idempotency-Key`.
- Persistida en la base del cliente (`idempotency_keys`: llave, hash del cuerpo, respuesta, TTL 7 días).
- La misma llave con otro cuerpo devuelve 422 `IDEMPOTENCIA_CONFLICTO`.

### 15.9 Auditoría

Columnas: `created_at`, `created_by`, `updated_at`, `updated_by`, `version`. `audit_log` append-only para precios, impuestos, tasas, usuarios, roles, permisos, anulaciones y cambios de costo estándar.

### 15.10 Errores (RFC 9457)

```json
{
  "type": "https://galaxy-erp.local/errores/stock-insuficiente",
  "title": "Stock insuficiente",
  "status": 409,
  "code": "STOCK_INSUFICIENTE",
  "detail": "ACEITE-1L en PRINCIPAL: disponible 3, solicitado 5",
  "trace_id": "9f2c...",
  "errors": []
}
```

El cliente muestra mensajes a partir de `code`, no de `detail`. Los códigos son estables y se documentan.

---

## 16. Modelo de datos base

Ejemplo del núcleo en cada base de cliente. Las demás tablas siguen el patrón.

```sql
CREATE TABLE company (
    id            uuid PRIMARY KEY DEFAULT uuidv7(),
    rif           varchar(20)  NOT NULL UNIQUE,
    razon_social  varchar(200) NOT NULL,
    contribuyente varchar(20)  NOT NULL DEFAULT 'ORDINARIO',   -- ORDINARIO | ESPECIAL
    moneda_base   char(3)      NOT NULL DEFAULT 'VES',
    activa        boolean      NOT NULL DEFAULT true
);

CREATE TABLE warehouse (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    company_id uuid NOT NULL REFERENCES company(id),
    codigo varchar(20) NOT NULL, nombre varchar(120) NOT NULL,
    activo boolean NOT NULL DEFAULT true,
    UNIQUE (company_id, codigo)
);

CREATE TABLE product (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    company_id uuid NOT NULL REFERENCES company(id),
    categoria_id uuid NOT NULL REFERENCES categoria(id),
    codigo varchar(40) NOT NULL, codigo_barras varchar(40),
    descripcion varchar(200) NOT NULL, unidad varchar(10) NOT NULL,
    costo_estandar numeric(18,4) NOT NULL DEFAULT 0,
    alicuota_iva_id uuid NOT NULL REFERENCES alicuota_iva(id),
    minimo numeric(18,4), maximo numeric(18,4),
    activo boolean NOT NULL DEFAULT true,
    version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(), created_by uuid NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(), updated_by uuid NOT NULL,
    UNIQUE (company_id, codigo)
);

CREATE TABLE stock_balance (
    company_id uuid NOT NULL,
    warehouse_id uuid NOT NULL REFERENCES warehouse(id),
    product_id uuid NOT NULL REFERENCES product(id),
    cantidad numeric(18,4) NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    PRIMARY KEY (company_id, warehouse_id, product_id)
);

CREATE TABLE stock_movement (                       -- kardex inmutable
    id bigserial PRIMARY KEY,
    company_id uuid NOT NULL, warehouse_id uuid NOT NULL, product_id uuid NOT NULL,
    tipo varchar(30) NOT NULL,                      -- COMPRA, VENTA, TRASLADO_IN, AJUSTE...
    documento_id uuid NOT NULL,
    cantidad numeric(18,4) NOT NULL,                -- + entrada, - salida
    costo_std numeric(18,4) NOT NULL,
    fecha timestamptz NOT NULL, created_by uuid NOT NULL
);

CREATE TABLE alicuota_iva (
    id uuid PRIMARY KEY DEFAULT uuidv7(),
    codigo varchar(20) NOT NULL,                    -- EXENTO, REDUCIDA, GENERAL, ADICIONAL
    porcentaje numeric(5,2) NOT NULL,
    vigente_desde date NOT NULL, vigente_hasta date,
    fuente text NOT NULL                            -- referencia normativa
);

CREATE TABLE tasa_cambio (
    fecha date NOT NULL, moneda char(3) NOT NULL,
    valor numeric(18,6) NOT NULL, fuente varchar(20) NOT NULL,
    PRIMARY KEY (fecha, moneda, fuente)
);

CREATE TABLE correlativo (
    company_id uuid NOT NULL, tipo varchar(30) NOT NULL, serie varchar(10) NOT NULL DEFAULT '',
    ultimo bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (company_id, tipo, serie)
);

CREATE TABLE idempotency_keys (
    llave uuid PRIMARY KEY, hash_cuerpo text NOT NULL,
    respuesta jsonb, estado_http integer, creado_en timestamptz NOT NULL DEFAULT now()
);
```

`stock_balance.CHECK (cantidad >= 0)` es la última defensa. La política de vender sin stock se valida antes, en el servicio. `stock_movement` y `audit_log` son append-only (privilegios limitados para `erp_app`).

---

## 17. Fiscalidad venezolana

> **Advertencia:** alícuotas, porcentajes de retención y formatos de libros y facturas cambian por providencias del SENIAT. Antes de cada versión fiscal, valida con un contador público colegiado. Este plan no sustituye esa validación.

### 17.1 Parametrizable en tablas, nunca en código

- **IVA:** alícuotas general, reducida, adicional y exento, con vigencia por fecha.
- **Retención de IVA:** porcentaje por tipo de contribuyente y operación.
- **Retención de ISLR:** conceptos, porcentajes y sustraendo.
- **IGTF** u otros impuestos que apliquen a ciertas operaciones en divisas: parametrizables y confirmados con el contador.
- **Tasa BCV:** carga diaria automática con respaldo manual.
- **RIF:** letra (V, E, J, G, P, C) y dígitos, con validación del dígito verificador.

### 17.2 Documentos fiscales

- Número de factura y número de control correlativos por empresa, sin huecos.
- Datos exigidos por la normativa vigente: RIF de emisor y receptor, fecha, base imponible, IVA desglosado, retenciones.
- Emisor en un módulo separado (`impuestos/emision`) para cambiar de formato sin tocar `ventas` (la facturación electrónica y la imprenta digital están en evolución regulatoria).

### 17.3 Libros y declaraciones

- Libro de ventas y de compras generados desde vistas SQL con el formato vigente.
- Declaración de IVA como reporte exportable. El sistema no presenta declaraciones ante el SENIAT.

### 17.4 Pruebas fiscales (casos dorados)

`tests/fiscal/`: una factura de ejemplo por combinación de alícuota, retención y tasa, resultado calculado a mano y **aprobado por el contador**. Ningún cambio en `impuestos` se fusiona sin pasarlas.

---

## 18. Sincronización offline

### 18.1 Principios

1. El dispositivo es un **cliente con cola de operaciones**, no una réplica completa.
2. Cada operación lleva `client_op_id` (UUID) y se guarda en Drift antes de mostrarse como hecha.
3. El servidor **valida todo** al sincronizar. El dispositivo nunca es la autoridad.
4. Los catálogos se descargan con un `sync_token` incremental.
5. Un dispositivo pertenece a un cliente y a una empresa; no cambia de cliente.

### 18.2 Descarga de catálogos

```
GET /api/v1/sync/catalogos?desde=<token>
→ { "token": "...", "productos": [...], "precios": [...], "clientes": [...],
    "stock": [...], "eliminados": [...] }
```

Token = número de secuencia por empresa. Solo cambios desde el último token. Los registros eliminados viajan en `eliminados`.

### 18.3 Subida de operaciones

```
POST /api/v1/sync/operaciones
{ "dispositivo_id": "...",
  "operaciones": [ { "client_op_id": "uuid", "tipo": "PEDIDO_VENTA",
                     "creado_en": "...", "tasa_usada": "...", "payload": {...} } ] }
→ { "resultados": [ { "client_op_id": "...", "estado": "APLICADA|RECHAZADA|DUPLICADA",
                      "documento_id": "...", "numero": "...", "error": null } ] }
```

- Cada operación en su transacción; una rechazada no bloquea las demás.
- Orden por `creado_en` dentro de cada dispositivo.
- `DUPLICADA` = ya aplicada; el cliente la marca como enviada.

### 18.4 Numeración offline

- El servidor entrega a cada dispositivo un **bloque de números** (p. ej. 50) al conectarse.
- Los no usados se devuelven o se anulan con motivo registrado.
- Si la normativa exige número de control en el momento de la venta, se muestra "pendiente de número" hasta sincronizar. **Requiere validación fiscal** (pregunta 2).
- Alternativa más segura: offline solo toma **pedidos** y la factura se emite al sincronizar.

### 18.5 Conflictos

| Caso | Regla |
|---|---|
| Stock insuficiente al sincronizar | Política por empresa: aplicar parcial, rechazar o permitir stock negativo con alerta |
| Precio cambiado | Se respeta el precio local dentro de la tolerancia; si no, se marca para revisión |
| Tasa de cambio | Política por empresa: tasa de la fecha de venta o de la sincronización |
| Maestros (clientes, productos) | El servidor gana; sin edición offline de maestros |

### 18.6 Pruebas

- Red intermitente y reenvío del mismo lote dos veces.
- Dos dispositivos vendiendo el mismo producto con stock limitado.
- Reinicio de la app con operaciones pendientes.
- Cambio de tasa entre venta y sincronización.
- Token vencido durante la sincronización.

---

## 19. Contrato de la API

- Base: `/api/v1`. Versionado por prefijo.
- OpenAPI generado por FastAPI se publica en `docs/openapi.json` en cada CI.
- Auth: `Authorization: Bearer <jwt>`.
- Cabeceras: `Idempotency-Key` en escrituras, `X-Request-Id` opcional (si falta se genera).
- Paginación por **cursor** en listados transaccionales; por **página** en catálogos pequeños.
- Filtros por query string con lista blanca por endpoint.
- Fechas ISO 8601 con zona; montos como **cadenas decimales** en JSON para evitar errores de coma flotante.
- Acciones de estado como subrecursos: `POST /ventas/facturas/{id}/aprobar`, `/anular` (con `motivo`).
- Rutas de plataforma (`/plataforma/...`) separadas y solo para `plataforma_admin`.

Rutas ilustrativas:

```
POST /auth/login                      {cliente, usuario, password}
POST /auth/refresh
GET  /me                              usuario, empresas, permisos, módulos, branding
GET  /admin/productos?cursor=...&q=...
POST /ventas/facturas                 (borrador)
POST /ventas/facturas/{id}/aprobar
POST /ventas/facturas/{id}/anular     {motivo}
POST /cxc/cobros                      {documentos[], instrumentos[]}
GET  /reportes/{codigo}?formato=pdf|xlsx|csv&...filtros
GET  /sync/catalogos   POST /sync/operaciones
GET  /branding
```

---

## 20. Experiencia de usuario con Kite

### 20.1 Principios

1. **Lo frecuente en dos toques:** "Nueva venta", "Nuevo pedido", "Cobrar" siempre visibles.
2. **Búsqueda global** (`Ctrl+K` en escritorio) de productos, clientes y documentos.
3. **Estados consistentes:** Borrador (gris), Aprobado (verde), Anulado (rojo), Pendiente de sincronizar (ámbar). Siempre con texto o ícono además del color.
4. **Nada se pierde:** borradores con autoguardado; la app retoma donde quedó.
5. **Errores accionables:** dicen qué pasó y qué hacer.
6. **Permisos sin sorpresas:** si no puede, el botón no aparece; si aparece, funciona.
7. **Lenguaje del usuario**, no jerga técnica.
8. **Divulgación progresiva:** lo básico visible, lo avanzado en "Más opciones".

### 20.2 Formatos regionales

- Idioma: español (Venezuela), textos en archivos ARB.
- Montos: una sola convención en todo el sistema (miles con punto, decimales con coma), con símbolo (Bs, US$).
- Cuando un monto está en VES, mostrar la **tasa usada**.
- Fechas `dd/MM/yyyy`; zona `America/Caracas` (UTC-4).
- RIF con máscara automática (`J-12345678-9`).

### 20.3 Navegación (menú lateral de Kite)

Visible según permisos y módulos contratados:

```
Inicio
Ventas        → Pedidos · Facturas · Notas de crédito · Presupuestos · Cotizaciones
Compras       → Órdenes · Compras · Devoluciones · Notas de entrega
Inventario    → Productos · Movimientos · Traslados · Ajustes · Precios · Reposición
Terceros      → Clientes · Proveedores · Vendedores · Zonas
Cobranza/Pagos→ CxC · CxP · Cobros · Pagos
Bancos        → Cuentas · Transacciones · Conciliación
Impuestos     → Libro de ventas · Libro de compras · Retenciones · IVA
Reportes      → (grupos de la sección 14.6)
Configuración → Empresas · Depósitos · Categorías · Monedas · Tasas · Alícuotas ·
                Usuarios · Roles · Auditoría · Marca
```

### 20.4 Panel de inicio por rol

| Rol | Tarjetas |
|---|---|
| Administrador | Ventas del día, CxC vencidas, stock bajo mínimo, tasa del día, alertas |
| Vendedor | Meta del mes, pedidos pendientes, clientes con saldo vencido, estado de sincronización |
| Depósito | Traslados y recepciones pendientes, stock bajo mínimo |
| Contador | Libros pendientes, retenciones por declarar, conciliaciones abiertas |

Cada tarjeta enlaza a la lista filtrada correspondiente.

### 20.4.1 Primer uso: asistente de configuración

1. Datos de la empresa (RIF validado, razón social, tipo de contribuyente).
2. Monedas y tasa del día.
3. Depósitos.
4. Categorías.
5. Importar productos desde Excel con plantilla descargable y vista previa de errores.
6. Usuarios y roles.
7. Resumen y botón "Empezar a vender".

Cada paso se puede saltar y retomar. El panel muestra el porcentaje de avance.

### 20.5 Flujos clave

**Nueva venta**

1. Elegir o crear cliente sin salir del flujo.
2. Buscar producto por texto o código de barras; Enter agrega y deja el cursor listo.
3. Cantidad, precio y descuento editables en la línea; el precio viene de la lista vigente.
4. Totales en vivo: base, IVA por alícuota, retenciones estimadas, total en VES y USD.
5. Guardar borrador o aprobar (resumen y confirmación).
6. Éxito: número asignado; opciones imprimir, compartir PDF, nueva venta, cobrar.

**Cobro**

1. Desde la factura, botón "Cobrar".
2. Instrumento de pago (puede ser mixto).
3. Monto en la moneda del instrumento con conversión y tasa visibles.
4. Confirmar; el estado de cuenta se actualiza.

**Anulación**

1. Botón "Anular" solo con permiso.
2. Diálogo con motivo obligatorio y resumen de efectos (inventario, CxC).
3. Se genera movimiento compensatorio; el documento queda "Anulado" y visible.

**Modo vendedor (móvil)**

- Cuatro pestañas: Clientes, Vender, Pedidos, Sincronización.
- Catálogo con stock del depósito del vendedor.
- Indicador de conexión permanente y contador de operaciones pendientes.

### 20.6 Estados de pantalla obligatorios

Toda pantalla define: **cargando** (esqueletos), **vacío** (con acción sugerida), **error** (con reintento) y **sin conexión**.

### 20.7 Componentes

- Reutilizar de Kite: shell, tarjetas, tablas, gráficas, formularios, diálogos.
- Crear propios: editor de líneas de documento, selector de productos con código de barras, panel de totales fiscales, chip de estado, indicador de sincronización, selector de moneda y tasa.

### 20.8 Accesibilidad y campo

- Contraste WCAG AA; áreas de toque ≥ 48 dp; texto escalable; uso con una mano; modo oscuro.

### 20.9 Marca por cliente (white-label)

Logo, colores y nombre comercial por cliente desde `GET /branding`; plantillas de factura y reportes por empresa. Sin cambios de código por cliente.

---

## 21. Arquitectura del cliente Flutter

```
presentation (pantallas Kite + widgets propios)
      │
   Riverpod (providers y estado)
      │
 domain (casos de uso, modelos)
      │
  data ├── api   (cliente OpenAPI generado + interceptores)
       ├── local (Drift: cola offline, catálogos)
       └── sync  (motor de sincronización)
```

**Sesión**

- Login con código de cliente, usuario y contraseña; luego selección de empresa si hay varias.
- Tokens en `flutter_secure_storage`; refresh automático.
- Si el refresh falla, se conserva la cola offline y se pide reingresar sin perder datos.

**Motor de sincronización**

- Estados: `PENDIENTE`, `ENVIANDO`, `APLICADA`, `RECHAZADA`, `DUPLICADA`.
- Reintento con espera exponencial, tope 5 min.
- Disparadores: reconexión, apertura, cada 60 s con pendientes, botón manual.
- Rechazadas muestran motivo y permiten corregir y reenviar.
- Base local de Drift cifrada si el dispositivo guarda datos sensibles (SQLCipher).

**Multiplataforma**

- Android/iOS: vendedor y depósito.
- Escritorio y web: administración, reportes, configuración.
- Layout adaptativo (teléfono, tablet, escritorio).

**Generación del cliente**

```bash
openapi-generator-cli generate -i docs/openapi.json -g dart-dio -o mobile/packages/galaxy_api
```

---

## 22. Despliegue: Podman, Caddy, respaldos

### 22.1 Imágenes

`Containerfile` multi-etapa: compilación → imagen final mínima con dependencias de WeasyPrint (`libpango`, `libcairo`, fuentes) y sin herramientas de compilación. Usuario no root dentro del contenedor.

### 22.2 Quadlet (usuario `erp`, `~/.config/containers/systemd/`)

`redis.container`:

```ini
[Unit]
Description=Galaxy ERP Redis
[Container]
Image=docker.io/library/redis:7-alpine
Network=erp-net.network
EnvironmentFile=%h/galaxy-erp/deploy/env/redis.env
Exec=sh -c 'redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy noeviction --requirepass "$REDIS_PASSWORD"'
Volume=erp-redis-data:/data
[Service]
Restart=always
[Install]
WantedBy=default.target
```

`api.container`:

```ini
[Unit]
Description=Galaxy ERP API
After=redis.service
[Container]
Image=localhost/galaxy-api:latest
Network=erp-net.network
EnvironmentFile=%h/galaxy-erp/deploy/env/api.env
Exec=uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers
Volume=erp-files:/data/files
HealthCmd=curl -fsS http://localhost:8000/salud
[Service]
Restart=always
[Install]
WantedBy=default.target
```

`worker.container`: misma imagen, `Exec=python -m app.workers.main`. **Un solo** contenedor ejecuta el planificador.

`caddy.container`: publica 443, monta certificados y el build web de Flutter.

### 22.3 Caddyfile

```caddy
galaxy-erp.<tu-tailnet>.ts.net {
    tls /certs/galaxy.crt /certs/galaxy.key
    encode zstd gzip

    handle /api/* {
        reverse_proxy api:8000
    }
    handle {
        root * /srv/web
        try_files {path} /index.html
        file_server
    }
    log {
        output stdout
        format json
    }
}
```

### 22.4 Respaldos

Timer diario a las 02:00, un respaldo **por cliente activo** y de `erp_control`:

```bash
for db in $(erpctl tenant listar --solo-db); do
  pg_dump -Fc -h 127.0.0.1 -p 5432 -U erp_owner "$db" \
    | gpg --batch --encrypt --recipient backup@galaxy \
    > /var/backups/erp/${db}_$(date +%F).dump.gpg
done
rclone copy /var/backups/erp/ remote:galaxy-backups/
find /var/backups/erp -name '*.gpg' -mtime +3 -delete    # local corto por el disco de 20 GB
```

- Retención externa: 30 días (configurable por contrato).
- Para menor pérdida de datos considera archivado de WAL (`pgBackRest` o `wal-g`) cuando haya clientes de pago.
- **Prueba de restauración mensual** de un cliente en una base temporal: conteos, cuadre de saldos, inicio de sesión de prueba. Un respaldo que nunca se restauró no existe.

### 22.5 Actualizaciones

1. Construir imagen nueva y etiquetarla con versión.
2. `erpctl migrar` canario → resto.
3. Reiniciar `api` y `worker`.
4. Verificar `/salud` y una prueba de humo.
5. Rollback: imagen anterior + `downgrade` probado.

Ventana de mantenimiento acordada con los clientes.

---

## 23. Operación y monitoreo

| Qué | Cómo | Alerta |
|---|---|---|
| Disco | Script diario `df` + `pg_database_size` | > 75 % |
| RAM | `free`, métricas de contenedor | Margen < 500 MB por 10 min |
| PostgreSQL | Conexiones y bloqueos | > 30 conexiones o bloqueo > 60 s |
| API | 5xx y p95 de latencia | 5xx > 1 % o p95 > 1 s |
| Respaldos | Último éxito | > 26 h |
| Sincronización | Operaciones `RECHAZADA` sin resolver | > 24 h |
| Certificado | Días para vencer | < 15 días |
| Tasa BCV | Carga del día | Sin tasa a las 10:00 |

- Alertas por correo o Telegram. Sin Grafana ni Loki por límite de memoria.
- Logs JSON con `timestamp`, `nivel`, `tenant_id`, `company_id`, `usuario_id`, `ruta`, `trace_id`, `duracion_ms`. Nunca contraseñas, tokens ni datos fiscales completos.
- Endpoint `/salud` (liveness) y `/salud/lista` (readiness: BD de control y Redis).

---

## 24. Calidad, pruebas y CI

| Nivel | Qué prueba |
|---|---|
| Unitarias | Reglas de negocio, dinero, validación de RIF |
| Integración | Endpoints contra PostgreSQL 18 real (testcontainers) |
| Aislamiento | Un cliente no ve datos de otro; una empresa no ve a otra (obligatoria) |
| Fiscales | Casos dorados de IVA y retenciones (obligatoria en `impuestos`) |
| Propiedades | Saldo = suma del kardex; CxC/CxP cuadran |
| Sincronización | Red intermitente, duplicados, conflictos |
| Migraciones | Upgrade y downgrade en base vacía y con datos |
| Carga | 10 usuarios concurrentes con k6 o Locust, antes del piloto |
| Flutter | Widgets y pruebas de integración de flujos clave |

**Pipeline**

1. Ruff y mypy
2. Unitarias
3. Integración
4. Aislamiento y fiscales
5. Generar `openapi.json` y compilar cliente Flutter contra él
6. Construir imágenes
7. Pruebas Flutter

Ninguna fusión a `main` sin todo verde.

**Git:** ramas `main`, `develop`, `feature/<modulo>-<desc>`, `hotfix/<desc>`; commits convencionales (`feat(inventario): ...`); un ADR por decisión arquitectónica.

---

## 25. Roadmap con tareas por fase

> Estimación para 1 a 2 desarrolladores. Se ajusta tras el primer sprint real.

### Fase 0: Plataforma (3 semanas)

- [ ] Repositorio, `Makefile`, `pyproject.toml`, Ruff, mypy, pytest
- [ ] Servidor preparado (sección 7)
- [ ] `core/`: configuración, logging, errores RFC 9457, dinero, tiempo
- [ ] `erp_control` + migración + modelos
- [ ] `erpctl`: `control init`, `tenant crear/listar/suspender/activar`, `migrar`
- [ ] Resolución de tenant, motores, RLS, caché de registro
- [ ] Módulo `identidad`: usuarios, roles, permisos, login, refresh, auditoría
- [ ] Pruebas de aislamiento
- [ ] CI, `Containerfile`, Quadlet, Caddy, respaldos con restauración probada

**Salida:** dos clientes de prueba creados y aislados; restauración exitosa.

### Fase 1: Administración (3 semanas)

- [ ] Empresas, depósitos, categorías, productos, proveedores, clientes, zonas, vendedores, instrumentos de pago, tipos de operación
- [ ] Monedas, tasas BCV (carga automática + manual), alícuotas
- [ ] Importación de productos desde Excel
- [ ] Correlativos
- [ ] Flutter: shell Kite, login, selector de empresa, CRUD de catálogos, asistente de configuración, marca por cliente

**Salida:** CRUD completo con permisos, auditoría y aislamiento.

### Fase 2: Inventario (3 semanas)

- [ ] Kardex, saldos, cargos, descargos, traslados, ajustes
- [ ] Costo estándar y variaciones
- [ ] Mínimos y máximos (propuesta y aprobación)
- [ ] Precios manuales y automáticos con vigencia
- [ ] Reportes de inventario y lista de precios
- [ ] Flutter: productos, movimientos, traslados, ajustes, reposición

**Salida:** propiedad saldo = kardex pasa.

### Fase 3: Compras y ventas (4 semanas)

- [ ] Compras: cotización, orden, anulación, compra, devolución, nota de entrega y su devolución
- [ ] Ventas: cotización, presupuesto, anulación, pedido, devolución, factura, nota de crédito
- [ ] Integración con inventario y CxC/CxP por servicios
- [ ] Flutter: flujo "Nueva venta", editor de líneas, panel de totales

**Salida:** ciclo completo de estados con efectos en inventario.

### Fase 4: Finanzas (3 semanas)

- [ ] Cuentas bancarias, beneficiarios, transacciones
- [ ] CxC y CxP, aplicación de pagos, antigüedad
- [ ] Conciliación bancaria
- [ ] Flutter: flujo "Cobro", estados de cuenta

**Salida:** saldos conciliables; antigüedad verificada.

### Fase 5: Impuestos y reportes (3 semanas)

- [ ] Motor fiscal: IVA, retenciones, IGTF si aplica
- [ ] Libros de ventas y compras, declaración de IVA
- [ ] Motor de reportes declarativo con PDF, XLSX y CSV
- [ ] Reportes pendientes de los grupos de la sección 14.6

**Salida:** casos fiscales aprobados por el contador.

### Fase 6: Sincronización (3 semanas)

- [ ] Endpoints de sync, `sync_token`, bloques de numeración
- [ ] Resolución de conflictos y políticas por empresa
- [ ] Pruebas de red intermitente y duplicados

### Fase 7: App de campo (4 semanas)

- [ ] Drift, cola offline, motor de sync
- [ ] Modo vendedor y depósito, escáner de códigos de barras
- [ ] Impresión o compartir PDF desde el móvil

**Salida:** piloto real con un vendedor durante una semana.

### Fase 8: Piloto y endurecimiento (2 semanas)

- [ ] Datos reales, pruebas de carga, restauración
- [ ] Ajustes de UX con usuarios reales
- [ ] Documentación de usuario y de operación

**Salida:** piloto sin incidentes críticos; primer cliente de pago.

---

## 26. Definición de terminado

- [ ] Endpoints en OpenAPI con ejemplos
- [ ] Pruebas unitarias e integración con PostgreSQL 18
- [ ] Prueba de aislamiento entre clientes y entre empresas
- [ ] Permisos aplicados en el servicio
- [ ] `company_id` presente y RLS activo
- [ ] Auditoría donde corresponde
- [ ] Migración reversible probada
- [ ] Dinero con `Decimal` y casos de borde
- [ ] Impuestos: casos dorados aprobados
- [ ] Inventario y finanzas: propiedad saldo = kardex
- [ ] Pantallas con estados cargando, vacío, error y sin conexión
- [ ] Textos en español (Venezuela) y formatos regionales
- [ ] ADR si introduce una decisión

---

## 27. Preguntas abiertas

| # | Pregunta | Afecta |
|---|---|---|
| 1 | ¿Modelo SaaS en tu VPS o instalación en el servidor del cliente? | Despliegue, actualizaciones, respaldos |
| 2 | ¿Se puede emitir factura sin número de control en el momento offline? | Numeración y sincronización |
| 3 | ¿Política de stock offline: permitir negativo o rechazar? | Conflictos |
| 4 | ¿Tasa de la fecha de venta o de la sincronización? | Dinero |
| 5 | ¿Listas de precio por cliente, zona, vendedor o una general? | Precios |
| 6 | ¿Cómo se clasifica cada cliente y proveedor (ordinario/especial)? | Retenciones |
| 7 | ¿Quién define el formato de libros: contador de cada empresa o formato interno? | Libros |
| 8 | ¿Un usuario trabaja en varias empresas a la vez o cambia al iniciar sesión? | Sesión |
| 9 | ¿Cuántos vendedores, Android o iOS, teléfono o tablet? | Flutter |
| 10 | ¿Destino de respaldos externos? | Respaldos |
| 11 | ¿La licencia de Kite permite uso comercial y redistribución? | Base de la UI |
| 12 | ¿Qué recuperación y pérdida máxima de datos ofreces por contrato? | Respaldos, WAL |
| 13 | ¿Módulos por separado o plan completo? | `tenant_modulo`, precios |
| 14 | ¿Aceptas "Categorías" en lugar de "Instancias" en la UI? | Lenguaje |
| 15 | ¿Tamaño de disco previsto? 20 GB limita el número de clientes | Capacidad |
| 16 | ¿Cómo obtienes la tasa BCV (fuente y mecanismo automático)? | Tasas |

**Prioritarias antes de la Fase 1:** 1, 2, 6, 11 y 15.

---

## 28. Cómo trabajar con Claude en cada fase

Pide un entregable acotado por vez. Plantilla:

```
Contexto: plan-galaxy-erp.md, Fase N.
Objetivo: <módulo o tarea concreta>
Entrega: código + migración + pruebas (unitarias, integración, aislamiento)
Restricciones: reglas de la sección 15, DoD de la sección 26
```

Orden sugerido de las primeras sesiones:

1. `pyproject.toml`, `Containerfile`, `core/` y `Makefile`.
2. `erp_control`: migración y modelos.
3. `tenancy/`: registro, motores, dependencia de sesión y pruebas de aislamiento.
4. `erpctl tenant crear` completo.
5. Migración inicial del tenant: `company`, `usuario`, `rol`, `permiso`, `audit_log`, `idempotency_keys`, `correlativo`.
6. `identidad`: login, refresh, permisos.
7. Quadlet, Caddy y respaldos.
8. Módulo `admin` y shell Kite.

**Regla de oro:** no avanzar de fase sin cumplir su criterio de salida.
