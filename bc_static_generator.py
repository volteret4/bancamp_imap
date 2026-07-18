#!/usr/bin/env python3
"""
Script CORRECTO para generar HTML estático con embeds de Bandcamp
USA EL ALBUM_ID/TRACK_ID DE BANDCAMP (ej: album_1212060845)
Esto es lo que Bandcamp usa internamente y es 100% único
"""

import os
import re
import json
from pathlib import Path
from html import escape, unescape
from collections import defaultdict
import argparse
from datetime import datetime

import bc_db

# Coincide exactamente con el bloque que genera generate_static_genre_html
# más abajo — se usa para recuperar los embeds ya publicados de una página
# existente antes de regenerarla.
_EMBED_ITEM_RE = re.compile(
    r'<div class="embed-item[^"]*"[^>]*data-embed-id="(?P<id>[^"]+)">'
    r'\s*(?P<embed>.*?)\s*'
    r'<div class="embed-info">\s*<strong>(?P<subject>.*?)</strong><br>\s*'
    r'<small>📅 (?P<date>.*?)</small>',
    re.DOTALL,
)


def _load_existing_embeds(filepath):
    """
    Extrae los embeds ya publicados en un HTML generado por esta misma
    función en una ejecución anterior. Necesario porque cada corrida de
    bc_export_to_json.py solo trae los correos NUEVOS no leídos (los ya
    procesados se marcan \\Seen y no reaparecen); sin esto, regenerar la
    página de un género con solo los embeds de HOY borraría el histórico
    acumulado en ejecuciones previas.
    """
    if not os.path.exists(filepath):
        return {}
    try:
        html_text = Path(filepath).read_text(encoding="utf-8")
    except OSError:
        return {}

    recovered = {}
    for m in _EMBED_ITEM_RE.finditer(html_text):
        bandcamp_id = m.group("id")
        recovered[bandcamp_id] = {
            "embed": m.group("embed").strip(),
            "subject": unescape(m.group("subject")),
            "date": unescape(m.group("date")),
            "date_obj": datetime.min,
        }
    return recovered


def extract_bandcamp_id(embed_code):
    """
    Extrae el album_id o track_id del código embed de Bandcamp.
    Ejemplo: album=1212060845 → "album_1212060845"
    """
    if not embed_code:
        return None

    # Buscar album=XXXXXXXX
    album_match = re.search(r'album=(\d+)', embed_code)
    if album_match:
        return f"album_{album_match.group(1)}"

    # Buscar track=XXXXXXXX
    track_match = re.search(r'track=(\d+)', embed_code)
    if track_match:
        return f"track_{track_match.group(1)}"

    return None


def generate_static_genre_html(genre, embeds, output_dir, items_per_page=10):
    """
    Genera un archivo HTML estático para un género específico.
    USA ALBUM_ID DE BANDCAMP como identificador único.
    """
    safe_genre = re.sub(r'[^\w\s-]', '', genre).strip().replace(' ', '_')
    filename = f"{safe_genre}.html"

    # Fusiona con lo ya publicado en el archivo existente (ver
    # _load_existing_embeds): cada corrida solo trae los correos NUEVOS no
    # leídos, así que sin esto se perdería el histórico acumulado.
    merged_by_id = _load_existing_embeds(os.path.join(output_dir, filename))
    for e in embeds:
        bandcamp_id = extract_bandcamp_id(e.get('embed')) or f"embed_{id(e)}"
        merged_by_id[bandcamp_id] = e
    embeds = list(merged_by_id.values())

    # Descarta los ya marcados como escuchados (servidor, vía /api/listened)
    # antes de ordenar/paginar, para que la paginación no quede con huecos.
    already_listened = bc_db.listened_ids()
    embeds = [
        e for e in embeds
        if extract_bandcamp_id(e.get('embed')) not in already_listened
    ]

    # Ordenar embeds por fecha (más reciente primero)
    embeds_sorted = sorted(
        embeds,
        key=lambda x: x.get('date_obj') or datetime.min,
        reverse=True
    )

    total_items = len(embeds_sorted)
    total_pages = (total_items + items_per_page - 1) // items_per_page

    # Generar los embeds HTML con botón de "Escuchado"
    embeds_html = ""
    for i, embed_data in enumerate(embeds_sorted):
        page_num = (i // items_per_page) + 1
        page_class = f"page-{page_num}" if total_pages > 1 else ""

        # CRÍTICO: Usar album_id de Bandcamp
        embed_id = extract_bandcamp_id(embed_data['embed'])

        if not embed_id:
            # Fallback: usar índice si no se encuentra ID
            embed_id = f"embed_{i}"
            print(f"  ⚠️  No se encontró album_id para: {embed_data.get('subject', 'Sin título')[:50]}")

        embeds_html += f"""
        <div class="embed-item {page_class}" data-page="{page_num}" id="{embed_id}" data-embed-id="{embed_id}">
            {embed_data['embed']}
            <div class="embed-info">
                <strong>{escape(embed_data.get('subject', 'Sin título'))}</strong><br>
                <small>📅 {escape(embed_data.get('date', 'Fecha desconocida'))}</small>
            </div>
            <div class="embed-actions">
                <button class="action-btn listened-btn" onclick="markAsListened('{embed_id}')">
                    🎧 Marcar como escuchado
                </button>
            </div>
        </div>
        """

    # Generar controles de paginación
    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        for page in range(1, total_pages + 1):
            active = "active" if page == 1 else ""
            pagination_html += f'<button class="page-btn {active}" data-page="{page}">Página {page}</button>'
        pagination_html += '</div>'

    # HTML completo con localStorage usando album_id de Bandcamp
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎵 {escape(genre)} - Bandcamp Collection</title>
    <link rel="icon" type="image/png" href="images/bandcamp.png">
    <link rel="stylesheet" href="theme-palettes.css">
    <style>
        [data-theme="og"], :root:not([data-theme]) {{
            --bg: #14141e;
            --surface: rgba(30, 30, 45, 0.95);
            --surface-2: #2d1b4e;
            --border: #667eea;
            --text: #e0e0e0;
            --text-muted: #b0b0b0;
            --accent: #9d7dff;
            --accent-2: #667eea;
            --success: #4CAF50;
            --warning: #f4a742;
            --danger: #f44336;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, var(--bg) 0%, var(--surface-2) 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: var(--surface);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }}

        h1 {{
            color: var(--text);
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 1.1em;
            margin-bottom: 15px;
        }}

        .back-link {{
            display: inline-block;
            margin-top: 15px;
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }}

        .back-link:hover {{
            color: #764ba2;
        }}

        .reset-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-left: 20px;
            padding: 8px 16px;
            min-height: 44px;
            background: var(--danger);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.3s;
        }}

        .reset-btn:hover {{
            background: #da190b;
            transform: translateY(-2px);
        }}

        .stats {{
            margin-top: 15px;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
            color: var(--text);
        }}

        .embeds-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}

        .embed-item {{
            background: var(--surface);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            min-width: 0;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s, opacity 0.3s;
        }}

        .embed-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }}

        .embed-item.hidden {{
            display: none;
        }}

        .embed-item.listened {{
            opacity: 0;
            transform: scale(0.8);
            pointer-events: none;
        }}

        .embed-item iframe,
        .embed-item embed {{
            max-width: 100%;
        }}

        .embed-info {{
            margin-top: 15px;
            color: #c0c0c0;
            font-size: 0.9em;
            overflow-wrap: break-word;
            word-break: break-word;
        }}

        .embed-actions {{
            margin-top: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .action-btn {{
            flex: 1;
            min-width: 150px;
            min-height: 44px;
            padding: 10px 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9em;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}

        .listened-btn {{
            background: var(--success);
            color: white;
        }}

        .listened-btn:hover {{
            background: #45a049;
            transform: translateY(-2px);
        }}

        .listened-btn:disabled {{
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }}

        .pagination {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 30px;
        }}

        .page-btn {{
            background: var(--surface);
            border: 2px solid var(--accent-2);
            color: var(--accent);
            padding: 10px 20px;
            min-height: 44px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }}

        .page-btn:hover {{
            background: var(--accent-2);
            color: white;
        }}

        .page-btn.active {{
            background: var(--accent-2);
            color: white;
        }}

        .notification {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            background: white;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            display: none;
            animation: slideIn 0.3s ease;
        }}

        .notification.show {{
            display: block;
        }}

        .notification.success {{
            border-left: 4px solid var(--success);
        }}

        @keyframes slideIn {{
            from {{
                transform: translateX(400px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}

        @media (max-width: 768px) {{
            .embeds-grid {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 2em;
                overflow-wrap: break-word;
            }}

            .action-btn {{
                min-width: 100%;
            }}
        }}

        @media (max-width: 480px) {{
            body {{
                padding: 12px;
            }}

            header {{
                padding: 20px;
            }}

            h1 {{
                font-size: 1.5em;
            }}

            .embed-item {{
                padding: 15px;
            }}

            .reset-btn {{
                margin-left: 0;
                margin-top: 10px;
            }}

            .notification {{
                left: 16px;
                right: 16px;
                max-width: calc(100% - 32px);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎵 {escape(genre)}</h1>
            <p class="subtitle">💿 <span id="visible-count">{total_items}</span> de {total_items} disco{"s" if total_items != 1 else ""}</p>
            <div class="stats">
                <strong>📊 Estadísticas:</strong>
                <div style="margin-top: 8px;">
                    ✅ Escuchados: <span id="listened-count">0</span> |
                    👂 Pendientes: <span id="pending-count">{total_items}</span>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <a href="index.html" class="back-link">← Volver al índice</a>
                <button class="reset-btn" onclick="resetListened()">🔄 Restaurar todos</button>
            </div>
        </header>

        <div class="embeds-grid" id="embeds-container">
            {embeds_html}
        </div>

        {pagination_html}
    </div>

    <div id="notification" class="notification"></div>

    <script>
        const STORAGE_KEY = 'bandcamp_listened_{safe_genre}';
        const TOTAL_ITEMS = {total_items};

        // Cargar estado guardado al iniciar
        function loadListenedState() {{
            const listened = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            let hiddenCount = 0;

            listened.forEach(embedId => {{
                const element = document.querySelector(`[data-embed-id="${{embedId}}"]`);
                if (element) {{
                    element.classList.add('listened');
                    setTimeout(() => {{
                        element.style.display = 'none';
                    }}, 500);
                    hiddenCount++;
                }}
            }});

            updateStats(hiddenCount);

            console.log('💾 Loaded listened:', listened);
        }}

        // Actualizar estadísticas
        function updateStats(listenedCount) {{
            const pending = TOTAL_ITEMS - listenedCount;
            document.getElementById('listened-count').textContent = listenedCount;
            document.getElementById('pending-count').textContent = pending;
            document.getElementById('visible-count').textContent = pending;
        }}

        // Marcar como escuchado (servidor — SQLite — es la fuente de verdad;
        // localStorage se mantiene solo para el feedback visual inmediato)
        function markAsListened(embedId) {{
            const element = document.getElementById(embedId);
            const button = element.querySelector('.listened-btn');

            // Deshabilitar botón
            button.disabled = true;
            button.textContent = '✅ Escuchado';

            fetch('/api/listened', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{id: embedId}}),
            }}).catch(err => console.error('No se pudo guardar en el servidor:', err));

            // Guardar en localStorage (feedback local, redundante con el servidor)
            const listened = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            if (!listened.includes(embedId)) {{
                listened.push(embedId);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(listened));
                console.log('✅ Marked as listened:', embedId);
            }}

            // Animar desaparición
            element.classList.add('listened');

            setTimeout(() => {{
                element.style.display = 'none';
                updateStats(listened.length);
            }}, 500);

            showNotification('¡Marcado como escuchado!', 'success');
        }}

        // Resetear todos los escuchados
        function resetListened() {{
            if (!confirm('¿Restaurar todos los discos? Aparecerán de nuevo los que marcaste como escuchados.')) {{
                return;
            }}

            localStorage.removeItem(STORAGE_KEY);

            // Mostrar todos los elementos
            document.querySelectorAll('.embed-item').forEach(item => {{
                item.classList.remove('listened');
                item.style.display = '';
                const button = item.querySelector('.listened-btn');
                button.disabled = false;
                button.textContent = '🎧 Marcar como escuchado';
            }});

            updateStats(0);
            showNotification('Todos los discos restaurados', 'success');
        }}

        // Paginación
        const pageButtons = document.querySelectorAll('.page-btn');
        const embedItems = document.querySelectorAll('.embed-item');

        pageButtons.forEach(button => {{
            button.addEventListener('click', () => {{
                const page = button.dataset.page;

                pageButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                embedItems.forEach(item => {{
                    if (item.classList.contains('listened')) {{
                        return;
                    }}

                    if (item.dataset.page === page) {{
                        item.classList.remove('hidden');
                    }} else {{
                        item.classList.add('hidden');
                    }}
                }});

                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
        }});

        // Mostrar solo la primera página al cargar
        if (pageButtons.length > 0) {{
            embedItems.forEach(item => {{
                if (item.dataset.page !== '1' && !item.classList.contains('listened')) {{
                    item.classList.add('hidden');
                }}
            }});
        }}

        // Notificaciones
        function showNotification(message, type = 'success') {{
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification show ${{type}}`;

            setTimeout(() => {{
                notification.classList.remove('show');
            }}, 3000);
        }}

        // Cargar estado al iniciar la página
        loadListenedState();

        console.log('🔑 Usando album_id/track_id de Bandcamp como identificador único');
        console.log('💾 Storage key:', STORAGE_KEY);

        // Función para detener otros reproductores de Bandcamp
        function stopOtherPlayers(currentIframe) {{
            const allIframes = document.querySelectorAll('iframe[src*="bandcamp.com"]');
            allIframes.forEach(iframe => {{
                if (iframe !== currentIframe) {{
                    const src = iframe.src;
                    iframe.src = '';
                    iframe.src = src;
                }}
            }});
        }}

        // Detectar cuando se reproduce un embed
        document.querySelectorAll('.embed-item').forEach(embedItem => {{
            embedItem.addEventListener('click', (e) => {{
                const iframe = embedItem.querySelector('iframe[src*="bandcamp.com"]');
                if (iframe && !e.target.classList.contains('action-btn')) {{
                    setTimeout(() => {{
                        stopOtherPlayers(iframe);
                    }}, 100);
                }}
            }});
        }});
    </script>
    <script src="theme-picker.js"></script>
</body>
</html>
"""

    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename


def generate_index_html(genres_data, output_dir):
    """
    Genera un index.html con enlaces a todos los géneros.
    """
    genres_html = ""
    total_albums = sum(data['count'] for data in genres_data.values())

    for genre, data in sorted(genres_data.items()):
        genres_html += f"""
        <div class="genre-card">
            <a href="{data['filename']}" class="genre-link">
                <h2>🎵 {escape(genre)}</h2>
                <p class="count">💿 {data['count']} disco{"s" if data['count'] != 1 else ""}</p>
            </a>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎵 Mi Colección de Bandcamp</title>
    <link rel="stylesheet" href="theme-palettes.css">
    <style>
        [data-theme="og"], :root:not([data-theme]) {{
            --bg: #14141e;
            --surface: rgba(30, 30, 45, 0.95);
            --surface-2: #2d1b4e;
            --border: #667eea;
            --text: #e0e0e0;
            --text-muted: #b0b0b0;
            --accent: #9d7dff;
            --accent-2: #667eea;
            --success: #4CAF50;
            --warning: #f4a742;
            --danger: #f44336;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, var(--bg) 0%, var(--surface-2) 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: var(--surface);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        h1 {{
            color: var(--text);
            font-size: 3em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 1.2em;
        }}

        .genres-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}

        .genre-card {{
            background: var(--surface);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            min-width: 0;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}

        .genre-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }}

        .genre-link {{
            text-decoration: none;
            color: inherit;
            display: block;
        }}

        .genre-card h2 {{
            color: var(--accent);
            margin-bottom: 10px;
            font-size: 1.5em;
            overflow-wrap: break-word;
        }}

        .count {{
            color: var(--text-muted);
            font-size: 1.1em;
        }}

        .tools-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-top: 20px;
            padding: 12px 24px;
            min-height: 44px;
            background: linear-gradient(135deg, #9d7dff 0%, #7c5ce0 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(157, 125, 255, 0.3);
        }}

        .tools-link:hover {{
            background: linear-gradient(135deg, #b99dff 0%, #9d7dff 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(157, 125, 255, 0.4);
        }}

        footer {{
            margin-top: 40px;
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2em;
                overflow-wrap: break-word;
            }}

            .genres-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 480px) {{
            body {{
                padding: 12px;
            }}

            header {{
                padding: 20px;
            }}

            h1 {{
                font-size: 1.5em;
            }}

            .genre-card {{
                padding: 20px;
            }}

            .tools-link {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎵 Mi Colección de Bandcamp</h1>
            <p class="subtitle">💿 {total_albums} álbumes en {len(genres_data)} género{"s" if len(genres_data) != 1 else ""}</p>
            <div style="margin-top: 20px;">
                <a href="sync_tools.html" class="tools-link">🔧 Sincronizar Colección</a>
            </div>
        </header>

        <div class="genres-grid">
            {genres_html}
        </div>

        <footer>
            <p>Generado con 💜 para disfrutar la música</p>
            <p style="margin-top: 10px; font-size: 0.85em;">
                Usando album_id de Bandcamp como identificador único
            </p>
        </footer>
    </div>
    <script src="theme-picker.js"></script>
</body>
</html>
"""

    filepath = os.path.join(output_dir, 'index.html')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Genera HTML estático con embeds de Bandcamp (USA ALBUM_ID DE BANDCAMP)'
    )

    parser.add_argument('--input', required=True,
                       help='Archivo JSON con los datos de los embeds')
    parser.add_argument('--output-dir', default='docs',
                       help='Directorio de salida (default: docs para GitHub Pages)')
    parser.add_argument('--items-per-page', type=int, default=10,
                       help='Número de discos por página (default: 10)')

    args = parser.parse_args()

    # Leer datos del JSON
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo {args.input}")
        print("Debes exportar tus datos primero usando bc_export_to_json.py")
        return
    except json.JSONDecodeError:
        print(f"❌ Error al leer el archivo JSON")
        return

    # Crear directorio de salida
    os.makedirs(args.output_dir, exist_ok=True)

    print("\n" + "="*80)
    print("🎵 GENERADOR DE COLECCIÓN ESTÁTICA DE BANDCAMP")
    print("="*80 + "\n")
    print("🔑 Usando album_id/track_id de Bandcamp como identificador único")

    # Organizar por género
    embeds_by_genre = {}
    for genre, embeds in data.items():
        # Convertir fechas string a objetos datetime para ordenar
        for embed in embeds:
            if 'date' in embed and embed['date']:
                try:
                    embed['date_obj'] = datetime.strptime(
                        embed['date'],
                        "%a, %d %b %Y %H:%M:%S %z"
                    )
                except:
                    embed['date_obj'] = datetime.min
            else:
                embed['date_obj'] = datetime.min

        embeds_by_genre[genre] = embeds

    # Generar HTMLs por género
    genres_data = {}
    total_embeds = sum(len(embeds) for embeds in embeds_by_genre.values())

    print(f"📊 Total de embeds: {total_embeds}")
    print(f"🎸 Géneros: {len(embeds_by_genre)}\n")

    for genre, embeds in sorted(embeds_by_genre.items()):
        if not embeds:
            continue

        print(f"  Generando {genre}... ({len(embeds)} discos)")
        filename = generate_static_genre_html(
            genre, embeds, args.output_dir, args.items_per_page
        )

        genres_data[genre] = {
            'filename': filename,
            'count': len(embeds)
        }

    # Generar index.html
    print(f"\n  Generando index.html...")
    generate_index_html(genres_data, args.output_dir)

    # Copiar sync_tools.html si existe
    sync_tools_path = os.path.join(os.path.dirname(__file__), 'sync_tools.html')
    if os.path.exists(sync_tools_path):
        import shutil
        dest_path = os.path.join(args.output_dir, 'sync_tools.html')
        shutil.copy2(sync_tools_path, dest_path)
        print(f"  Copiando sync_tools.html...")

    print("\n" + "="*80)
    print(f"✅ Sitio generado en: {args.output_dir}")
    print("="*80 + "\n")
    print("🔑 IMPORTANTE:")
    print("   • Usando album_id de Bandcamp (ej: album_1212060845)")
    print("   • Este ID es único y estable para cada álbum")
    print("   • No requiere hashing ni cálculos adicionales")
    print("\n📝 PRÓXIMOS PASOS:")
    print("   1. Sube el directorio a tu repositorio de GitHub")
    print("   2. Ve a Settings → Pages")
    print("   3. Selecciona la rama y la carpeta /docs")
    print("   4. ¡Tu colección estará online!")
    print("\n💾 Los álbumes escuchados se guardan en localStorage")
    print("🔄 Sincroniza con bc_sync.py para eliminar los escuchados")
    print()


if __name__ == '__main__':
    main()
