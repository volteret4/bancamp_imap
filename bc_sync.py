#!/usr/bin/env python3
"""
Script para sincronizar tu colección:
1. Lee localStorage exportado desde el navegador
2. Exporta nuevos correos del IMAP
3. Elimina del JSON los álbumes marcados como escuchados
4. Añade los nuevos álbumes encontrados
5. Genera HTML actualizado

Uso:
    1. Exporta localStorage desde el navegador (ver instrucciones)
    2. Ejecuta este script con --localStorage-file
"""

import json
import argparse
import os
import sys
import getpass
from datetime import datetime
from collections import defaultdict

# Importar funciones del script de exportación
sys.path.insert(0, os.path.dirname(__file__))
from bc_imap_generator import (
    IMAPConfig,
    IMAPSessionManager,
    interactive_setup,
    process_imap_folder
)


def load_listened_from_browser(localStorage_file):
    """
    Lee el archivo JSON exportado del navegador y extrae los IDs escuchados.

    El archivo debe tener este formato:
    {
        "bandcamp_listened_Rock": ["embed_123", "embed_456"],
        "bandcamp_listened_Jazz": ["embed_789"]
    }
    """
    try:
        with open(localStorage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        listened_by_genre = {}

        for key, value in data.items():
            if key.startswith('bandcamp_listened_'):
                # Extraer el género del key
                genre = key.replace('bandcamp_listened_', '')

                # value es una lista de IDs
                if isinstance(value, list):
                    listened_by_genre[genre] = set(value)
                elif isinstance(value, str):
                    # Si está como string, parsearlo
                    listened_by_genre[genre] = set(json.loads(value))

        return listened_by_genre

    except FileNotFoundError:
        print(f"⚠️  Archivo no encontrado: {localStorage_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al leer JSON: {e}")
        return {}


def load_existing_json(json_file):
    """
    Carga el JSON existente con la colección.
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ℹ️  No existe {json_file}, se creará uno nuevo")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al leer {json_file}: {e}")
        return {}


def get_embed_id(url):
    """
    Genera el mismo ID que usa el HTML para un embed.
    Debe coincidir con la lógica en bc_static_generator.py
    """
    return f"embed_{abs(hash(url))}"


def filter_listened_albums(embeds, listened_ids):
    """
    Filtra los álbumes que ya han sido escuchados.

    Args:
        embeds: Lista de embeds
        listened_ids: Set de IDs escuchados

    Returns:
        Lista de embeds NO escuchados
    """
    filtered = []
    removed_count = 0

    for embed in embeds:
        embed_id = get_embed_id(embed['url'])

        if embed_id not in listened_ids:
            filtered.append(embed)
        else:
            removed_count += 1

    return filtered, removed_count


def merge_collections(old_data, new_data, listened_by_genre):
    """
    Fusiona la colección antigua con la nueva:
    1. Elimina los escuchados de old_data
    2. Añade los nuevos de new_data
    3. Elimina duplicados

    Returns:
        (merged_data, stats)
    """
    merged = defaultdict(list)
    stats = {
        'removed': 0,
        'added': 0,
        'kept': 0,
        'by_genre': {}
    }

    all_genres = set(list(old_data.keys()) + list(new_data.keys()))

    for genre in all_genres:
        genre_stats = {'removed': 0, 'added': 0, 'kept': 0}

        old_embeds = old_data.get(genre, [])
        new_embeds = new_data.get(genre, [])
        listened_ids = listened_by_genre.get(genre, set())

        # Filtrar escuchados de la colección antigua
        kept_embeds, removed = filter_listened_albums(old_embeds, listened_ids)
        genre_stats['removed'] = removed
        genre_stats['kept'] = len(kept_embeds)

        # Crear set de URLs existentes para evitar duplicados
        existing_urls = {embed['url'] for embed in kept_embeds}

        # Añadir nuevos embeds (que no estén duplicados)
        added = 0
        for embed in new_embeds:
            if embed['url'] not in existing_urls:
                kept_embeds.append(embed)
                existing_urls.add(embed['url'])
                added += 1

        genre_stats['added'] = added

        # Solo incluir géneros con contenido
        if kept_embeds:
            merged[genre] = kept_embeds

        stats['by_genre'][genre] = genre_stats
        stats['removed'] += removed
        stats['added'] += added
        stats['kept'] += len(kept_embeds)

    return dict(merged), stats


def export_new_emails(config, folders, mark_as_read, include_read):
    """
    Exporta nuevos correos desde IMAP.
    """
    try:
        session = IMAPSessionManager.get_instance()
        mail = session.connect(config)
    except Exception as e:
        print(f"\n❌ No se pudo conectar al servidor IMAP")
        print(f"Error: {e}")
        return None

    try:
        embeds_by_genre = {}

        for folder_spec in folders:
            if ':' in folder_spec:
                folder_name, genre = folder_spec.rsplit(':', 1)
            else:
                folder_name = folder_spec
                genre = folder_name.split('/')[-1]

            embeds = process_imap_folder(
                mail, folder_name, genre,
                mark_as_read=mark_as_read,
                include_read=include_read,
                delete_after=False,
                config=config
            )

            if genre not in embeds_by_genre:
                embeds_by_genre[genre] = []
            embeds_by_genre[genre].extend(embeds)

        return embeds_by_genre

    finally:
        session.disconnect()


def save_json(data, output_file):
    """
    Guarda los datos a JSON.
    """
    # Preparar datos para JSON (convertir datetime a string)
    export_data = {}

    for genre, embeds in data.items():
        export_data[genre] = []
        for embed in embeds:
            embed_copy = embed.copy()

            # Convertir datetime a string para JSON
            if 'date_obj' in embed_copy:
                if isinstance(embed_copy['date_obj'], datetime):
                    embed_copy['date_obj'] = embed_copy['date_obj'].isoformat()
                else:
                    embed_copy['date_obj'] = None

            export_data[genre].append(embed_copy)

    # Guardar a JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)


def print_stats(stats):
    """
    Imprime estadísticas de la sincronización.
    """
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS DE SINCRONIZACIÓN")
    print("="*80)
    print(f"\n✓ Álbumes mantenidos: {stats['kept']}")
    print(f"➕ Álbumes nuevos añadidos: {stats['added']}")
    print(f"➖ Álbumes escuchados eliminados: {stats['removed']}")
    print(f"\nTotal final: {stats['kept']} álbumes")

    if stats['by_genre']:
        print("\n📁 Por género:")
        for genre, genre_stats in sorted(stats['by_genre'].items()):
            total = genre_stats['kept']
            added = genre_stats['added']
            removed = genre_stats['removed']

            if total > 0 or added > 0 or removed > 0:
                print(f"\n  {genre}:")
                print(f"    • Mantenidos: {genre_stats['kept'] - added}")
                print(f"    • Nuevos: {added}")
                print(f"    • Eliminados: {removed}")
                print(f"    • Total: {total}")


def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza tu colección de Bandcamp con localStorage y nuevos correos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flujo de trabajo:
  1. Exporta localStorage desde tu navegador (ver --help-export)
  2. Ejecuta este script con --localStorage-file
  3. El script eliminará álbumes escuchados y añadirá nuevos
  4. Regenera el sitio con bc_static_generator.py

Ejemplos:
  # Solo sincronizar sin buscar nuevos correos
  python3 bc_sync.py --localStorage-file browser_data.json --no-fetch

  # Sincronizar y buscar nuevos correos
  python3 bc_sync.py --localStorage-file browser_data.json --interactive \\
    --folders "INBOX/Rock:Rock"

  # Solo eliminar escuchados (sin buscar nuevos)
  python3 bc_sync.py --localStorage-file browser_data.json --no-fetch \\
    --input bandcamp_data.json
        """
    )

    # Opciones de localStorage
    parser.add_argument('--localStorage-file',
                       help='Archivo JSON con localStorage exportado del navegador')
    parser.add_argument('--help-export', action='store_true',
                       help='Muestra instrucciones para exportar localStorage')

    # Opciones de datos
    parser.add_argument('--input', default='bandcamp_data.json',
                       help='Archivo JSON actual (default: bandcamp_data.json)')
    parser.add_argument('--output', default='bandcamp_data_synced.json',
                       help='Archivo JSON de salida (default: bandcamp_data_synced.json)')

    # Opciones de IMAP
    parser.add_argument('--no-fetch', action='store_true',
                       help='NO buscar nuevos correos, solo eliminar escuchados')
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para configurar IMAP')
    parser.add_argument('--server', help='Servidor IMAP')
    parser.add_argument('--port', type=int, default=993)
    parser.add_argument('--email', help='Email')
    parser.add_argument('--password', help='Contraseña')
    parser.add_argument('--folders', nargs='+',
                       help='Carpetas en formato "ruta:género"')
    parser.add_argument('--no-mark-read', action='store_true',
                       help='NO marcar correos como leídos')
    parser.add_argument('--include-read', action='store_true',
                       help='Incluir correos ya leídos')

    args = parser.parse_args()

    # Mostrar ayuda de exportación
    if args.help_export:
        print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           CÓMO EXPORTAR LOCALSTORAGE DESDE TU NAVEGADOR              ║
╚═══════════════════════════════════════════════════════════════════════╝

Opción 1: Consola del navegador (Recomendado)
────────────────────────────────────────────────

1. Abre tu colección de Bandcamp en el navegador
2. Presiona F12 para abrir DevTools
3. Ve a la pestaña "Console"
4. Copia y pega este código:

   // Exportar localStorage
   const data = {};
   Object.keys(localStorage)
     .filter(key => key.startsWith('bandcamp_listened_'))
     .forEach(key => {
       data[key] = JSON.parse(localStorage.getItem(key));
     });

   // Descargar como archivo
   const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
   const url = URL.createObjectURL(blob);
   const a = document.createElement('a');
   a.href = url;
   a.download = 'browser_data.json';
   a.click();

5. Se descargará el archivo browser_data.json
6. Usa ese archivo con --localStorage-file


Opción 2: Manualmente (más tedioso)
────────────────────────────────────

1. F12 → Application (o Storage)
2. Local Storage → tu-sitio
3. Copia los valores de cada clave que empiece con "bandcamp_listened_"
4. Crea un JSON manualmente:

   {
     "bandcamp_listened_Rock": ["embed_123", "embed_456"],
     "bandcamp_listened_Jazz": ["embed_789"]
   }


Opción 3: Extensión de navegador
─────────────────────────────────

Usa una extensión como "LocalStorage Manager" para exportar los datos.


Una vez tengas el archivo:
───────────────────────────

python3 bc_sync.py --localStorage-file browser_data.json --interactive \\
  --folders "INBOX/Rock:Rock"

""")
        return

    print("\n" + "="*80)
    print("🔄 SINCRONIZACIÓN DE COLECCIÓN BANDCAMP")
    print("="*80)

    # Cargar localStorage si se proporciona
    listened_by_genre = {}
    if args.localStorage_file:
        print(f"\n📥 Cargando localStorage desde: {args.localStorage_file}")
        listened_by_genre = load_listened_from_browser(args.localStorage_file)

        if listened_by_genre:
            total_listened = sum(len(ids) for ids in listened_by_genre.values())
            print(f"✓ {total_listened} álbumes marcados como escuchados")
            for genre, ids in listened_by_genre.items():
                print(f"  • {genre}: {len(ids)} escuchados")
        else:
            print("⚠️  No se encontraron datos de escuchados")

    # Cargar JSON existente
    print(f"\n📂 Cargando colección actual: {args.input}")
    old_data = load_existing_json(args.input)

    if old_data:
        total_old = sum(len(embeds) for embeds in old_data.values())
        print(f"✓ {total_old} álbumes en la colección actual")
    else:
        print("ℹ️  No hay colección previa")

    # Buscar nuevos correos si se solicita
    new_data = {}
    if not args.no_fetch:
        if not args.folders:
            print("\n⚠️  No se especificaron carpetas. Usa --folders o --no-fetch")
            print("Ejemplo: --folders \"INBOX/Rock:Rock\"")
            return

        print("\n📧 Buscando nuevos correos...")

        # Configurar IMAP
        if args.interactive:
            config = interactive_setup()
        elif args.server and args.email:
            password = args.password or getpass.getpass(f"Contraseña para {args.email}: ")
            config = IMAPConfig(args.server, args.port, args.email, password)
        else:
            print("❌ Debes usar --interactive o proporcionar --server y --email")
            return

        mark_as_read = not args.no_mark_read
        new_data = export_new_emails(
            config, args.folders, mark_as_read, args.include_read
        )

        if new_data:
            total_new = sum(len(embeds) for embeds in new_data.values())
            print(f"✓ {total_new} álbumes encontrados en correos")
        else:
            print("ℹ️  No se encontraron nuevos álbumes")
    else:
        print("\n⏭️  Saltando búsqueda de nuevos correos (--no-fetch)")

    # Fusionar colecciones
    print("\n🔄 Sincronizando...")
    merged_data, stats = merge_collections(old_data, new_data, listened_by_genre)

    # Guardar resultado
    save_json(merged_data, args.output)
    print(f"\n✅ Colección sincronizada guardada en: {args.output}")

    # Mostrar estadísticas
    print_stats(stats)

    print("\n" + "="*80)
    print("✅ SINCRONIZACIÓN COMPLETADA")
    print("="*80)

    print("\n📝 PRÓXIMOS PASOS:")
    print(f"   1. Revisa el archivo: {args.output}")
    print(f"   2. Regenera el sitio:")
    print(f"      python3 bc_static_generator.py --input {args.output}")
    print(f"   3. Sube los cambios a GitHub")
    print()


if __name__ == '__main__':
    main()
