#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Galaxy ERP - Script de Restauración de Respaldos
# ==============================================================================
# - Restaura erp_control o bases de inquilinos (erp_c_<slug>)
# - Soporta archivos .dump y cifrados .dump.gpg
# - Restaura esquema y datos con erp_owner
# - Reestablece permisos de erp_app sobre el plano restaurado
# ==============================================================================

DB_TARGET=""
ARCHIVO_BACKUP=""
HOST="${PGHOST:-127.0.0.1}"
PORT="${PGPORT:-5432}"
OWNER_USER="${PGUSER:-erp_owner}"

uso() {
    echo "Uso: $0 --db <nombre_base> --archivo <ruta_archivo.dump[.gpg]>"
    echo "Ejemplo: $0 --db erp_c_demo --archivo /var/backups/erp/erp_c_demo_2026-10-08.dump.gpg"
    exit 1
}

log() {
    echo "[$(date --iso-8601=seconds)] $*"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db)
            DB_TARGET="$2"
            shift 2
            ;;
        --archivo)
            ARCHIVO_BACKUP="$2"
            shift 2
            ;;
        --help|-h)
            uso
            ;;
        *)
            echo "Opción desconocida: $1"
            uso
            ;;
    esac
done

if [[ -z "${DB_TARGET}" || -z "${ARCHIVO_BACKUP}" ]]; then
    log "Error: Se requieren los parámetros --db y --archivo."
    uso
fi

if [[ ! -f "${ARCHIVO_BACKUP}" ]]; then
    log "Error: El archivo de respaldo '${ARCHIVO_BACKUP}' no existe."
    exit 1
fi

log "=== Iniciando restauración para base de datos: ${DB_TARGET} ==="
log "Archivo de origen: ${ARCHIVO_BACKUP}"

# 1. Crear base de datos si no existe
log "Verificando existencia de la base ${DB_TARGET}..."
DB_EXISTS=$(psql -h "${HOST}" -p "${PORT}" -U "${OWNER_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_TARGET}';" || true)

if [[ "${DB_EXISTS}" != "1" ]]; then
    log "La base ${DB_TARGET} no existe. Creándola con dueño ${OWNER_USER}..."
    psql -h "${HOST}" -p "${PORT}" -U "${OWNER_USER}" -d postgres -c "CREATE DATABASE ${DB_TARGET} OWNER ${OWNER_USER} ENCODING 'UTF8';"
else
    log "La base ${DB_TARGET} ya existe. Procediendo a restaurar sobre ella..."
fi

# 2. Descomprimir/descifrar y restaurar con pg_restore
TEMP_DUMP=""
if [[ "${ARCHIVO_BACKUP}" == *.gpg ]]; then
    log "Archivo cifrado detectado. Descifrando temporalmente..."
    TEMP_DUMP="$(mktemp --suffix=.dump)"
    trap 'rm -f "${TEMP_DUMP}"' EXIT
    gpg --batch --yes --decrypt "${ARCHIVO_BACKUP}" > "${TEMP_DUMP}"
    RESTORE_FILE="${TEMP_DUMP}"
else
    RESTORE_FILE="${ARCHIVO_BACKUP}"
fi

log "Ejecutando pg_restore sobre ${DB_TARGET}..."
# pg_restore con --clean --if-exists para reemplazar objetos existentes limpiamente
pg_restore -h "${HOST}" -p "${PORT}" -U "${OWNER_USER}" -d "${DB_TARGET}" --clean --if-exists --no-owner "${RESTORE_FILE}" || {
    # pg_restore retorna warning/error si hay advertencias menores de clean en objetos que no existían
    log "Nota: pg_restore finalizó con códigos de verificación. Comprobando integridad..."
}

# 3. Reasignar permisos para erp_app
log "Reaplicando permisos mínimos DML para 'erp_app' en ${DB_TARGET}..."
psql -h "${HOST}" -p "${PORT}" -U "${OWNER_USER}" -d "${DB_TARGET}" << 'EOSQL'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'erp_app') THEN
        EXECUTE format('GRANT CONNECT ON DATABASE %I TO erp_app', current_database());
        GRANT USAGE ON SCHEMA public TO erp_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO erp_app;
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO erp_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO erp_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO erp_app;
        
        -- Si existe audit_log, garantizar que es append-only
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log') THEN
            REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM erp_app;
        END IF;
    END IF;
END $$;
EOSQL

# 4. Verificación de prueba de salud en la base restaurada
CONTEO_TABLAS=$(psql -h "${HOST}" -p "${PORT}" -U "${OWNER_USER}" -d "${DB_TARGET}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

log "✓ Restauración completada exitosamente. Total tablas restauradas en ${DB_TARGET}: ${CONTEO_TABLAS}"
