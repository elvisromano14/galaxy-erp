#!/usr/bin/env bash
set -e

API_URL="${API_URL:-http://localhost:8000}"
SLUG="test"
USER="admin"
PASS="GalaxyTest2026!"

echo "======================================================================"
echo " GALAXY ERP — PRUEBA DE CONEXIÓN VÍA CURL"
echo " Servidor objetivo: $API_URL"
echo " Tenant objetivo:   $SLUG"
echo "======================================================================"

# 1. Healthcheck
echo -n "1. Verificando disponibilidad de la API ($API_URL/healthz)... "
if ! curl -sf "$API_URL/healthz" > /dev/null 2>&1; then
    echo "NO DISPONIBLE."
    echo "Inicie la API ejecutando en otra terminal: make api"
    exit 1
fi
echo "OK"

# 2. Login
echo -n "2. Autenticando con usuario '$USER' en empresa '$SLUG'... "
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"cliente\": \"$SLUG\", \"usuario\": \"$USER\", \"password\": \"$PASS\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "FALLO EN LOGIN"
    echo "$LOGIN_RESPONSE"
    exit 1
fi
echo "OK (JWT obtenido)"

# 3. Usuario actual
echo "3. Consultando /api/v1/auth/me..."
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/auth/me" | python3 -m json.tool

# 4. Productos
echo "4. Consultando productos (/api/v1/admin/productos)..."
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/admin/productos" | python3 -m json.tool

# 5. Clientes
echo "5. Consultando clientes y retenciones (/api/v1/admin/clientes)..."
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/admin/clientes" | python3 -m json.tool

echo "======================================================================"
echo " Conexión exitosa. Puedes probar interactivamente en: $API_URL/docs"
echo "======================================================================"
