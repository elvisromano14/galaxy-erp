#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Galaxy ERP - Script de Respaldo Diario Automatizado por Cliente
# ==============================================================================
# - Respalda erp_control y cada base activa de cliente (erp_c_<slug>)
# - Cifra con GPG usando clave pública de respaldo
# - Copia a almacenamiento remoto con rclone
# - Limpieza local a los 3 días (para cuidar el límite de disco de 20 GB)
# ==============================================================================

BACKUP_DIR="${BACKUP_DIR:-/var/backups/erp}"
GPG_RECIPIENT="${GPG_RECIPIENT:-backup@galaxy-erp.local}"
RCLONE_REMOTE="${RCLONE_REMOTE:-remote:galaxy-backups/}"
FECHA="$(date +%F_%H%M%S)"
RETENCION_DIAS="${RETENCION_DIAS:-3}"

mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date --iso-8601=seconds)] $*"
}

log "=== Iniciando ciclo de respaldos Galaxy ERP ==="

# 1. Obtener lista de bases a respaldar
# Incluye erp_control y todas las bases devueltas por erpctl
DATABASES=("erp_control")

if command -v erpctl >/dev/null 2>&1; then
    while IFS= read -r db; do
        [[ -n "${db}" ]] && DATABASES+=("${db}")
    done < <(erpctl tenant listar --solo-db)
else
    # Fallback si se ejecuta desde el repo directamente
    ERPCTL_CLI="$(dirname "$0")/../../api/cli/main.py"
    if [[ -f "${ERPCTL_CLI}" ]]; then
        while IFS= read -r db; do
            [[ -n "${db}" ]] && DATABASES+=("${db}")
        done < <(python3 "${ERPCTL_CLI}" tenant listar --solo-db)
    fi
fi

log "Bases de datos a respaldar: ${DATABASES[*]}"

# 2. Respaldar y cifrar cada base
EXITOSOS=0
FALLIDOS=0

for DB in "${DATABASES[@]}"; do
    DESTINO="${BACKUP_DIR}/${DB}_${FECHA}.dump.gpg"
    log "Respaldando base: ${DB} -> ${DESTINO}"

    if pg_dump -Fc -h 127.0.0.1 -p 5432 -U erp_owner "${DB}" | \
       gpg --batch --yes --encrypt --recipient "${GPG_RECIPIENT}" --output "${DESTINO}"; then
        log "✓ Respaldo completado para ${DB} ($(du -h "${DESTINO}" | cut -f1))"
        ((EXITOSOS++))
    else
        log "✗ ERROR al respaldar ${DB}"
        ((FALLIDOS++))
    fi
done

# 3. Sincronización remota con rclone si está configurado
if command -v rclone >/dev/null 2>&1 && [[ -n "${RCLONE_REMOTE}" ]]; then
    log "Sincronizando con almacenamiento remoto: ${RCLONE_REMOTE}..."
    if rclone copy "${BACKUP_DIR}" "${RCLONE_REMOTE}"; then
        log "✓ Sincronización remota exitosa."
    else
        log "⚠ Advertencia: Falló sincronización con rclone."
    fi
fi

# 4. Limpieza local de respaldos antiguos (retención corta por límite de 20 GB)
log "Limpiando respaldos locales con más de ${RETENCION_DIAS} días..."
find "${BACKUP_DIR}" -name '*.dump.gpg' -type f -mtime "+${RETENCION_DIAS}" -delete

log "=== Resumen de respaldos: ${EXITOSOS} exitosos, ${FALLIDOS} fallidos ==="

if [[ "${FALLIDOS}" -gt 0 ]]; then
    exit 1
fi
