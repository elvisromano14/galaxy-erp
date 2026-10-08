# Galaxy ERP

Galaxy ERP es un sistema ERP modular multi-tenant diseñado para Venezuela, con soporte bimoneda (VES / USD), cumplimiento fiscal ante el SENIAT, y arquitectura aislada por base de datos independiente para cada cliente.

## Arquitectura

- **Multi-tenancy:** 1 base de datos PostgreSQL por cliente (`erp_c_<slug>`), gestionadas mediante un plano de control central (`erp_control`).
- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy 2 (async) / PgBouncer / Redis 7.
- **Herramientas de Operación:** CLI unificado `erpctl` para aprovisionamiento, migraciones y mantenimiento.
- **Cliente:** Flutter (desktop, web y móvil para vendedores).

Para más detalles sobre la arquitectura y fases, consulta [plan-galaxy-erp.md](plan-galaxy-erp.md).
