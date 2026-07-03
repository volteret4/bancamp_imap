#!/usr/bin/env python3
import os
import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request, abort

import bc_db

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / 'docs'
DATA_JSON = BASE_DIR / 'bc_data.json'
UPDATE_TOKEN = os.environ.get('UPDATE_TOKEN', '')
UPDATE_SCRIPT = BASE_DIR / 'update.sh'

# ── Panel de configuración (⚙) ───────────────────────────────────────────────
# Mismo patrón que el resto de apps. update.sh hace "source .env" en cada
# ejecución (no via env_file de Docker), así que los cambios en IMAP_* aquí
# aplican en la siguiente actualización sin reiniciar el contenedor; solo
# UPDATE_TOKEN (leído una vez al arrancar Flask) necesita reinicio de verdad.
SETTINGS_ENV_PATH = BASE_DIR / ".env"
SETTINGS_PASSWORD = os.environ.get("SETTINGS_PASSWORD", "")
VARS_SPEC = [
    {"name": "IMAP_SERVER", "secret": False, "help": "Host del servidor IMAP"},
    {"name": "IMAP_PORT", "secret": False, "default": "993", "help": "Puerto IMAP (normalmente 993)"},
    {"name": "IMAP_EMAIL", "secret": False, "help": "Cuenta de correo a leer"},
    {"name": "IMAP_PASSWORD", "secret": True, "help": "Contraseña / contraseña de aplicación IMAP"},
    {"name": "IMAP_FOLDERS", "secret": False, "help": "Carpetas IMAP a escanear (separadas por espacio)"},
    {"name": "ITEMS_PER_PAGE", "secret": False, "default": "10", "help": "Álbumes por página en el HTML generado"},
    {"name": "UPDATE_TOKEN", "secret": True, "help": "Token del botón 'Actualizar colección' (requiere reiniciar el contenedor)"},
    {"name": "GH_PAT", "secret": True, "help": "Token de GitHub (fine-grained, contents:write sobre este repo) para publicar docs/ automáticamente"},
]
_HAS_SECRETS = any(v.get("secret") for v in VARS_SPEC)


def _read_env_file(path):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                v = v[1:-1]
            values[k.strip()] = v
    return values


def _write_env_file(path, updates):
    lines = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}\n")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            if out and not out[-1].endswith("\n"):
                out[-1] += "\n"
            out.append(f"{k}={v}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def _current_value(spec):
    file_vals = _read_env_file(SETTINGS_ENV_PATH)
    if spec["name"] in file_vals:
        return file_vals[spec["name"]]
    return os.environ.get(spec["name"], spec.get("default", ""))


def _check_auth(password):
    if not SETTINGS_PASSWORD:
        return not _HAS_SECRETS
    return password == SETTINGS_PASSWORD


@app.route("/api/settings", methods=["POST"])
def api_settings():
    d = request.get_json(silent=True) or {}
    password = d.get("password") or ""
    requires = bool(SETTINGS_PASSWORD) or _HAS_SECRETS
    authorized = _check_auth(password)
    if requires and not authorized:
        error = "Contraseña incorrecta" if password else None
        if not SETTINGS_PASSWORD:
            error = "Este servicio tiene credenciales pero no hay SETTINGS_PASSWORD configurada. Añádela al .env y reinicia el contenedor."
        return jsonify({"requires_password": True, "authorized": False, "error": error})
    vars_out = [
        {"name": v["name"], "value": _current_value(v), "secret": v["secret"], "help": v.get("help", "")}
        for v in VARS_SPEC
    ]
    return jsonify({"requires_password": requires, "authorized": True, "vars": vars_out})


@app.route("/api/settings/save", methods=["POST"])
def api_settings_save():
    d = request.get_json(silent=True) or {}
    if not _check_auth(d.get("password") or ""):
        return jsonify({"error": "Contraseña incorrecta"}), 403
    known = {v["name"] for v in VARS_SPEC}
    updates = {k: v for k, v in (d.get("values") or {}).items() if k in known}
    if not updates:
        return jsonify({"error": "Nada que guardar"}), 400
    _write_env_file(SETTINGS_ENV_PATH, updates)
    return jsonify({"ok": True, "message": "Guardado. IMAP_* aplican en la próxima actualización; UPDATE_TOKEN necesita reiniciar el contenedor."})

_state = {'running': False, 'last_update': None, 'last_status': None}
_lock = threading.Lock()

UPDATE_WIDGET = '''<div id="bc-update-widget" style="position:fixed;bottom:20px;right:20px;z-index:9999;
     background:rgba(30,30,45,0.97);border-radius:12px;padding:14px 18px;min-width:210px;
     box-shadow:0 5px 25px rgba(0,0,0,0.4);backdrop-filter:blur(10px);font-family:sans-serif;">
  <div id="bc-status" style="color:#b0b0b0;font-size:0.82em;margin-bottom:9px;"></div>
  <button id="bc-btn" onclick="bcUpdate()" style="
     background:linear-gradient(135deg,#9d7dff,#7c5ce0);color:white;border:none;
     border-radius:8px;padding:9px 16px;cursor:pointer;font-size:0.88em;
     font-weight:500;width:100%;transition:opacity .2s;">
    🔄 Actualizar colección
  </button>
</div>
<script>
(function(){
  const TOKEN = '__TOKEN__';
  const btn = () => document.getElementById('bc-btn');
  const status = () => document.getElementById('bc-status');

  function poll() {
    fetch('/api/status').then(r=>r.json()).then(d=>{
      if (d.running) {
        status().textContent = '⏳ Actualizando...';
        btn().disabled = true; btn().style.opacity = '0.5';
        setTimeout(poll, 3000);
      } else {
        const last = d.last_update ? new Date(d.last_update).toLocaleString('es') : 'Nunca';
        status().textContent = (d.last_status === 'ok' ? '✅ ' : d.last_status ? '❌ ' : '') + last;
        btn().disabled = false; btn().style.opacity = '1';
        if (d.last_status === 'ok' && window._bcWasRunning) location.reload();
      }
      window._bcWasRunning = d.running;
    }).catch(()=>{});
  }

  function bcUpdate() {
    btn().disabled = true; btn().style.opacity = '0.5';
    status().textContent = '⏳ Iniciando...';
    fetch('/api/update', {method:'POST', headers:{'X-Update-Token': TOKEN}})
      .then(r=>r.json()).then(d=>{
        if (!d.ok) { status().textContent = '❌ ' + (d.error||'Error'); btn().disabled=false; btn().style.opacity='1'; }
        else setTimeout(poll, 2000);
      }).catch(()=>{ btn().disabled=false; btn().style.opacity='1'; });
  }

  window.bcUpdate = bcUpdate;
  poll();
  setInterval(poll, 60000);
})();
</script>
<script src="/settings-panel.js"></script>'''


def _run_update_bg():
    try:
        result = subprocess.run(
            ['bash', str(UPDATE_SCRIPT)],
            capture_output=True, text=True,
            cwd=str(BASE_DIR), timeout=600
        )
        status = 'ok' if result.returncode == 0 else 'error'
    except Exception as e:
        status = 'error'
    finally:
        with _lock:
            _state['running'] = False
            _state['last_update'] = datetime.now().isoformat()
            _state['last_status'] = status


@app.route('/api/update', methods=['POST'])
def api_update():
    if UPDATE_TOKEN and request.headers.get('X-Update-Token') != UPDATE_TOKEN:
        abort(403)
    with _lock:
        if _state['running']:
            return jsonify({'ok': False, 'error': 'Ya hay una actualización en curso'})
        _state['running'] = True
    threading.Thread(target=_run_update_bg, daemon=True).start()
    return jsonify({'ok': True})


@app.route('/api/status')
def api_status():
    with _lock:
        return jsonify(dict(_state))


@app.route('/api/listened', methods=['POST'])
def api_listened():
    d = request.get_json(silent=True) or {}
    embed_id = d.get('id')
    if not embed_id:
        return jsonify({'ok': False, 'error': 'id requerido'}), 400
    bc_db.mark_listened(embed_id)
    # Regenera docs/ ya mismo (no solo en el próximo cron) para que desaparezca
    # de verdad, reutilizando el mismo generador que update.sh.
    if DATA_JSON.exists():
        items_per_page = os.environ.get('ITEMS_PER_PAGE', '10')
        subprocess.run(
            ['python3', 'bc_static_generator.py',
             '--input', str(DATA_JSON), '--output-dir', str(DOCS_DIR),
             '--items-per-page', items_per_page],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=60,
        )
    return jsonify({'ok': True})


@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    file_path = DOCS_DIR / path
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    if path.endswith('.html'):
        content = file_path.read_text(encoding='utf-8')
        widget = UPDATE_WIDGET.replace('__TOKEN__', UPDATE_TOKEN)
        content = content.replace('</body>', widget + '\n</body>')
        return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return send_from_directory(str(DOCS_DIR), path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(host=host, port=port, threaded=True)
