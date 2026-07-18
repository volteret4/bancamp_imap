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
# IMAP_FOLDERS va separado por "|" (no por espacio: los nombres de carpeta
# pueden llevar espacios, p.ej. "Musica.Synth Pop:Musica.Synth Pop"), así que
# no se puede expandir directo con IFS - se parte a un array explícito.
IFS='|' read -ra _IMAP_FOLDER_ARR <<< "${IMAP_FOLDERS}"

"$PYTHON" bc_export_to_json.py \
    --server "${IMAP_SERVER}" \
    --port   "${IMAP_PORT:-993}" \
    --email  "${IMAP_EMAIL}" \
    --password "${IMAP_PASSWORD}" \
    --output bc_data.json \
    --folders "${_IMAP_FOLDER_ARR[@]}"

# Regenerar HTML estático
log "Paso 2/2: Generando HTML estático..."
"$PYTHON" bc_static_generator.py \
    --input bc_data.json \
    --output-dir docs \
    --items-per-page "${ITEMS_PER_PAGE:-10}"

log "=== Actualización completada ==="
