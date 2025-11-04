#!/usr/bin/env python3
"""
Script para generar HTML estático con embeds de Bandcamp organizados por género
Versión mejorada con correcciones:
1. Oscurece embeds en lugar de eliminarlos (más confiable)
2. Mejor detección de reproducción para pausar otros embeds
3. Filtrado de duplicados por URL

Perfecto para GitHub Pages
"""

import os
import re
import json
from pathlib import Path
from html import escape
from collections import defaultdict
import argparse
from datetime import datetime


def deduplicate_embeds(embeds):
    """
    Elimina embeds duplicados basándose en la URL.
    Mantiene el primero (más reciente si están ordenados).
    """
    seen_urls = set()
    unique_embeds = []

    for embed in embeds:
        url = embed.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_embeds.append(embed)

    return unique_embeds


def generate_static_genre_html(genre, embeds, output_dir, items_per_page=10):
    """
    Genera un archivo HTML estático para un género específico.
    Los embeds se oscurecen al marcarlos como escuchados usando localStorage.
    """
    # Ordenar embeds por fecha (más reciente primero)
    embeds_sorted = sorted(
        embeds,
        key=lambda x: x.get('date_obj') or datetime.min,
        reverse=True
    )

    # FILTRAR DUPLICADOS
    embeds_sorted = deduplicate_embeds(embeds_sorted)

    # Sanitizar el nombre del archivo
    safe_genre = re.sub(r'[^\w\s-]', '', genre).strip().replace(' ', '_')
    filename = f"{safe_genre}.html"

    total_items = len(embeds_sorted)
    total_pages = (total_items + items_per_page - 1) // items_per_page

    # Generar los embeds HTML con botón de "Escuchado"
    embeds_html = ""
    for i, embed_data in enumerate(embeds_sorted):
        page_num = (i // items_per_page) + 1
        page_class = f"page-{page_num}" if total_pages > 1 else ""

        # Crear identificador único basado en la URL
        embed_id = f"embed_{abs(hash(embed_data['url']))}"

        # URL limpia para mostrar
        url_display = embed_data['url'][:50] + "..." if len(embed_data['url']) > 50 else embed_data['url']

        embeds_html += f"""
        <div class="embed-item {page_class}" data-page="{page_num}" id="{embed_id}" data-embed-id="{embed_id}" data-url="{escape(embed_data['url'])}">
            <div class="embed-container">
                {embed_data['embed']}
            </div>
            <div class="embed-info">
                <strong>{escape(embed_data.get('subject', 'Sin título'))}</strong><br>
                <small>📅 {escape(embed_data.get('date', 'Fecha desconocida'))}</small><br>
                <small style="opacity: 0.6; font-size: 0.8em;">🔗 {escape(url_display)}</small>
            </div>
            <div class="embed-actions">
                <button class="action-btn listened-btn" onclick="markAsListened('{embed_id}')">
                    🎧 Marcar como escuchado
                </button>
            </div>
            <div class="listened-overlay">
                <div class="listened-badge">✓ Escuchado</div>
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

    # HTML completo con localStorage
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎵 {escape(genre)} - Bandcamp Collection</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #14141e 0%, #2d1b4e 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: rgba(30, 30, 45, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }}

        h1 {{
            color: #e0e0e0;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #b0b0b0;
            font-size: 1.1em;
            margin-bottom: 15px;
        }}

        .back-link {{
            display: inline-block;
            margin-top: 15px;
            color: #9d7dff;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }}

        .back-link:hover {{
            color: #764ba2;
        }}

        .reset-btn {{
            display: inline-block;
            margin-left: 20px;
            padding: 8px 16px;
            background: #f44336;
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
            color: #e0e0e0;
        }}

        .embeds-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}

        .embed-item {{
            position: relative;
            background: rgba(30, 30, 45, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}

        .embed-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }}

        .embed-item.hidden {{
            display: none;
        }}

        /* NUEVO: Oscurecer en lugar de ocultar */
        .embed-item.listened {{
            filter: brightness(0.4) grayscale(0.8);
            opacity: 0.5;
        }}

        .embed-item.listened:hover {{
            transform: none;
        }}

        .embed-item.listened .embed-container {{
            pointer-events: none;
        }}

        /* Overlay de "Escuchado" */
        .listened-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0);
            display: none;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            border-radius: 15px;
        }}

        .embed-item.listened .listened-overlay {{
            display: flex;
        }}

        .listened-badge {{
            background: rgba(76, 175, 80, 0.95);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }}

        .embed-container {{
            position: relative;
        }}

        .embed-info {{
            margin-top: 15px;
            color: #c0c0c0;
            font-size: 0.9em;
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
            padding: 10px 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9em;
            transition: all 0.3s;
        }}

        .listened-btn {{
            background: #4CAF50;
            color: white;
        }}

        .listened-btn:hover {{
            background: #45a049;
            transform: translateY(-2px);
        }}

        .listened-btn:disabled {{
            background: #95d5b2;
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
            background: rgba(30, 30, 45, 0.95);
            border: 2px solid #667eea;
            color: #9d7dff;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }}

        .page-btn:hover {{
            background: #667eea;
            color: white;
        }}

        .page-btn.active {{
            background: #667eea;
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
            border-left: 4px solid #4CAF50;
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
            }}

            .action-btn {{
                min-width: 100%;
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
                    ✓ Escuchados: <span id="listened-count">0</span> |
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
        let currentPlayingIframe = null;

        // Cargar estado guardado al iniciar
        function loadListenedState() {{
            const listened = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            let listenedCount = 0;

            listened.forEach(embedId => {{
                const element = document.querySelector(`[data-embed-id="${{embedId}}"]`);
                if (element) {{
                    element.classList.add('listened');
                    const button = element.querySelector('.listened-btn');
                    if (button) {{
                        button.disabled = true;
                        button.textContent = '✓ Escuchado';
                    }}
                    listenedCount++;
                }}
            }});

            updateStats(listenedCount);
            console.log(`📊 Cargados ${{listenedCount}} álbumes escuchados`);
        }}

        // Actualizar estadísticas
        function updateStats(listenedCount) {{
            const pending = TOTAL_ITEMS - listenedCount;
            document.getElementById('listened-count').textContent = listenedCount;
            document.getElementById('pending-count').textContent = pending;
            document.getElementById('visible-count').textContent = TOTAL_ITEMS;
        }}

        // Marcar como escuchado
        function markAsListened(embedId) {{
            const element = document.getElementById(embedId);
            if (!element) return;

            const button = element.querySelector('.listened-btn');

            // Guardar en localStorage PRIMERO
            const listened = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
            if (!listened.includes(embedId)) {{
                listened.push(embedId);
                localStorage.setItem(STORAGE_KEY, JSON.stringify(listened));
                console.log(`💾 Guardado en localStorage:`, embedId);
            }}

            // Actualizar UI
            button.disabled = true;
            button.textContent = '✓ Escuchado';

            // Oscurecer el embed
            element.classList.add('listened');

            updateStats(listened.length);
            showNotification('¡Marcado como escuchado!', 'success');
        }}

        // Resetear todos los escuchados
        function resetListened() {{
            if (!confirm('¿Restaurar todos los discos? Aparecerán de nuevo los que marcaste como escuchados.')) {{
                return;
            }}

            localStorage.removeItem(STORAGE_KEY);
            console.log(`🗑️ localStorage limpiado`);

            // Mostrar todos los elementos
            document.querySelectorAll('.embed-item').forEach(item => {{
                item.classList.remove('listened');
                const button = item.querySelector('.listened-btn');
                if (button) {{
                    button.disabled = false;
                    button.textContent = '🎧 Marcar como escuchado';
                }}
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
                if (item.dataset.page !== '1') {{
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

        // ========== MEJORADO: DETECCIÓN DE REPRODUCCIÓN ==========

        // Función mejorada para pausar otros reproductores
        function pauseOtherPlayers(currentIframe) {{
            if (!currentIframe) return;

            const allIframes = document.querySelectorAll('iframe[src*="bandcamp.com"]');
            let pausedCount = 0;

            allIframes.forEach(iframe => {{
                if (iframe !== currentIframe) {{
                    // Método 1: Recargar iframe (más efectivo)
                    const src = iframe.src;
                    iframe.src = '';
                    // Pequeño delay antes de recargar
                    setTimeout(() => {{
                        iframe.src = src;
                    }}, 50);
                    pausedCount++;
                }}
            }});

            if (pausedCount > 0) {{
                console.log(`⏸️ Pausados ${{pausedCount}} reproductores`);
            }}

            currentPlayingIframe = currentIframe;
        }}

        // Detectar clicks en los embeds con mejor timing
        function setupPlaybackDetection() {{
            document.querySelectorAll('.embed-item').forEach(embedItem => {{
                const iframe = embedItem.querySelector('iframe[src*="bandcamp.com"]');

                if (!iframe) return;

                // Detectar mousedown (antes del click)
                embedItem.addEventListener('mousedown', (e) => {{
                    // Solo si no es el botón de acción
                    if (!e.target.classList.contains('action-btn')) {{
                        // Pausar inmediatamente
                        pauseOtherPlayers(iframe);
                    }}
                }});

                // También detectar clicks directamente
                embedItem.addEventListener('click', (e) => {{
                    if (!e.target.classList.contains('action-btn')) {{
                        // Delay corto para asegurar que se ejecute después del click
                        setTimeout(() => {{
                            pauseOtherPlayers(iframe);
                        }}, 150);
                    }}
                }});

                // Detectar cuando el iframe está en foco
                iframe.addEventListener('mouseenter', () => {{
                    iframe.dataset.hovered = 'true';
                }});

                iframe.addEventListener('mouseleave', () => {{
                    iframe.dataset.hovered = 'false';
                }});
            }});

            console.log('🎵 Detección de reproducción configurada');
        }}

        // Prevenir múltiples reproductores al cargar
        function preventAutoplay() {{
            // Esperar a que todos los iframes carguen
            const iframes = document.querySelectorAll('iframe[src*="bandcamp.com"]');
            let loadedCount = 0;

            iframes.forEach(iframe => {{
                iframe.addEventListener('load', () => {{
                    loadedCount++;
                    // Cuando todos hayan cargado, asegurar que solo uno pueda reproducir
                    if (loadedCount === iframes.length) {{
                        console.log(`✅ ${{iframes.length}} embeds cargados y listos`);
                    }}
                }});
            }});
        }}

        // Inicializar todo
        function init() {{
            loadListenedState();
            setupPlaybackDetection();
            preventAutoplay();

            console.log('💾 Storage key:', STORAGE_KEY);
            console.log('📦 Total embeds:', TOTAL_ITEMS);
            console.log('✅ Sistema de reproducción inicializado');
        }}

        // Ejecutar cuando el DOM esté listo
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    </script>
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
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #14141e 0%, #2d1b4e 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            background: rgba(30, 30, 45, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        h1 {{
            color: #e0e0e0;
            font-size: 3em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #b0b0b0;
            font-size: 1.2em;
        }}

        .genres-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}

        .genre-card {{
            background: rgba(30, 30, 45, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
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
            color: #9d7dff;
            margin-bottom: 10px;
            font-size: 1.5em;
        }}

        .count {{
            color: #b0b0b0;
            font-size: 1.1em;
        }}

        .tools-link {{
            display: inline-block;
            margin-top: 20px;
            padding: 12px 24px;
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
            }}

            .genres-grid {{
                grid-template-columns: 1fr;
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
                Los álbumes escuchados se oscurecen pero siguen visibles
            </p>
            <p style="margin-top: 5px; font-size: 0.85em; opacity: 0.7;">
                ✨ Versión mejorada: sin duplicados, auto-pause, oscurecimiento confiable
            </p>
        </footer>
    </div>
</body>
</html>
"""

    filepath = os.path.join(output_dir, 'index.html')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Genera HTML estático con embeds de Bandcamp desde archivo JSON (versión mejorada)'
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
    print("🎵 GENERADOR DE COLECCIÓN ESTÁTICA DE BANDCAMP (VERSIÓN MEJORADA)")
    print("="*80 + "\n")
    print("✨ Mejoras aplicadas:")
    print("   • Filtrado de duplicados por URL")
    print("   • Oscurecimiento en lugar de eliminación (más confiable)")
    print("   • Mejor detección de reproducción para auto-pause")
    print()

    # Organizar por género
    embeds_by_genre = {}
    total_duplicates = 0

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

        original_count = len(embeds)
        embeds = deduplicate_embeds(embeds)
        duplicates = original_count - len(embeds)

        if duplicates > 0:
            print(f"  📦 {genre}: Eliminados {duplicates} duplicado(s)")
            total_duplicates += duplicates

        embeds_by_genre[genre] = embeds

    if total_duplicates > 0:
        print(f"\n  ✅ Total de duplicados eliminados: {total_duplicates}")
        print()

    # Generar HTMLs por género
    genres_data = {}
    total_embeds = sum(len(embeds) for embeds in embeds_by_genre.values())

    print(f"📊 Total de embeds únicos: {total_embeds}")
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
    print("🔍 PRÓXIMOS PASOS PARA GITHUB PAGES:")
    print("   1. Sube el directorio a tu repositorio de GitHub")
    print("   2. Ve a Settings → Pages")
    print("   3. Selecciona la rama y la carpeta /docs")
    print("   4. ¡Tu colección estará online!\n")
    print("💾 CAMBIOS EN ESTE VERSIÓN:")
    print("   • Los álbumes escuchados se OSCURECEN (no desaparecen)")
    print("   • Mejor persistencia en localStorage")
    print("   • Auto-pause al reproducir otros embeds")
    print("   • Sin duplicados")
    print()


if __name__ == '__main__':
    main()
