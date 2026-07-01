#!/usr/bin/env python3
import os
import subprocess
import threading
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request, abort

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / 'docs'
UPDATE_TOKEN = os.environ.get('UPDATE_TOKEN', '')
UPDATE_SCRIPT = BASE_DIR / 'update.sh'

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
</script>'''


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
