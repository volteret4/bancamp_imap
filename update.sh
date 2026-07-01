#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Cargar variables de entorno
if [ -f .env ]; then
    set -a
    # shellcheck source=.env
    source .env
    set +a
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

VENV_PYTHON="$HOME/Scripts/python_venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="python3"
fi

log "=== Iniciando actualización de colección Bandcamp ==="

# Exportar correos IMAP a JSON
log "Paso 1/2: Exportando correos desde IMAP..."
"$PYTHON" bc_export_to_json.py \
    --server "${IMAP_SERVER}" \
    --port   "${IMAP_PORT:-993}" \
    --email  "${IMAP_EMAIL}" \
    --password "${IMAP_PASSWORD}" \
    --output bc_data.json \
    --folders ${IMAP_FOLDERS}

# Regenerar HTML estático
log "Paso 2/2: Generando HTML estático..."
"$PYTHON" bc_static_generator.py \
    --input bc_data.json \
    --output-dir docs \
    --items-per-page "${ITEMS_PER_PAGE:-10}"

log "=== Actualización completada ==="
