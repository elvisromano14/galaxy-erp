#!/usr/bin/env bash
# ==============================================================================
# GALAXY ERP — SCRIPT DE INSTALACIÓN Y DESPLIEGUE EN VPS (MODO PODMAN QUADLET)
# ==============================================================================
set -euo pipefail

REPO_URL="https://github.com/elvisromano14/galaxy-erp.git"
INSTALL_DIR="$HOME/galaxy-erp"
QUADLET_DIR="$HOME/.config/containers/systemd"

echo "======================================================================"
echo "    INSTALACIÓN Y ENDURECIMIENTO DE GALAXY ERP EN VPS"
echo "======================================================================"

# 1. Comprobar dependencias del sistema anfitrión
echo "[1/6] Verificando dependencias necesarias (podman, git, curl)..."
for cmd in podman git curl; do
    if ! command -v "$cmd" > /dev/null 2>&1; then
        echo "ERROR: El comando '$cmd' no está instalado en el VPS."
        echo "Instálelo con el gestor de paquetes de su distribución (apt, dnf o pacman)."
        exit 1
    fi
done
echo "  ✓ Dependencias básicas encontradas."

# 2. Clonar o actualizar el repositorio
echo "[2/6] Preparando código fuente en $INSTALL_DIR..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  • Repositorio existente. Actualizando rama main..."
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
else
    echo "  • Clonando repositorio oficial..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Crear entorno de producción si no existe
echo "[3/6] Verificando variables de entorno de producción (.env)..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "  • Creando archivo .env inicial a partir de la plantilla..."
    JWT_GEN=$(head -c 32 /dev/urandom | base64)
    cat << ENV_EOF > "$INSTALL_DIR/.env"
ENVIRONMENT=production
DEBUG=false
APP_NAME="Galaxy ERP"

# Conexiones PostgreSQL (ajuste con las credenciales de su PostgreSQL del VPS)
CONTROL_DB_URL=postgresql+asyncpg://erp_app:erp_app_pass@127.0.0.1:5432/erp_control
CONTROL_DB_OWNER_URL=postgresql+asyncpg://erp_owner:erp_owner_pass@127.0.0.1:5432/erp_control

REDIS_URL=redis://127.0.0.1:6379/0

# Clave secreta autogenerada para JWT
JWT_SECRET_KEY=$JWT_GEN
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Orígenes permitidos (CORS estricto en producción)
ALLOWED_ORIGINS=["https://galaxy-erp.tailscale.net"]

# Hardening
ENABLE_SECURITY_HEADERS=true
MAX_BODY_SIZE_MB=10
RATE_LIMIT_LOGIN_MAX=10
RATE_LIMIT_LOGIN_WINDOW_SECONDS=60

TIMEZONE=America/Caracas
ENV_EOF
    chmod 600 "$INSTALL_DIR/.env"
    echo "  ✓ Archivo .env generado con clave JWT segura. Por favor ajuste las URLs de PostgreSQL según su VPS."
fi

# 4. Compilar imagen de producción con Podman
echo "[4/6] Compilando imagen OCI 'galaxy-api:latest' con Podman..."
podman build -t galaxy-api:latest -f api/Containerfile api/
echo "  ✓ Imagen OCI compilada correctamente."

# 5. Instalar archivos Quadlet para administración autónoma con systemd
echo "[5/6] Instalando servicios systemd (Quadlet en modo usuario rootless)..."
mkdir -p "$QUADLET_DIR"
cp -f deploy/quadlet/* "$QUADLET_DIR/"

# Habilitar lingering para que los contenedores corran sin sesión SSH activa
loginctl enable-linger "$USER" || true

systemctl --user daemon-reload
echo "  ✓ Servicios Quadlet registrados."

# 6. Inicializar y verificar tenant canario de pruebas
echo "[6/6] Inicializando base de datos de control y empresa de pruebas..."
podman run --rm --network host --env-file "$INSTALL_DIR/.env" galaxy-api:latest erpctl control init || true
podman run --rm --network host --env-file "$INSTALL_DIR/.env" galaxy-api:latest erpctl test init || true

echo "======================================================================"
echo " ¡INSTALACIÓN COMPLETADA EXITOSAMENTE EN EL VPS!"
echo "======================================================================"
echo "Comandos para iniciar los servicios:"
echo "  • Iniciar API:      systemctl --user start galaxy-api"
echo "  • Iniciar Redis:    systemctl --user start redis"
echo "  • Ver estado:       systemctl --user status galaxy-api"
echo "  • Ver logs:         journalctl --user -u galaxy-api -f"
echo ""
echo "Acceso seguro por Tailscale:"
echo "  Para habilitar HTTPS automático dentro de su red Tailscale, ejecute:"
echo "  tailscale cert \$(tailscale status --json | grep -o '\"DNSName\": *\"[^\"]*' | cut -d'\"' -f4)"
echo "======================================================================"
