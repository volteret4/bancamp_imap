#!/usr/bin/env python3
"""
Script de sincronización CORREGIDO
Problema resuelto: Ya no reagrega álbumes que el usuario eliminó

Lógica correcta:
1. Álbumes en localStorage = fueron eliminados conscientemente por el usuario
2. NO deben reaparecer aunque sigan en los correos
3. Solo agregar álbumes verdaderamente NUEVOS (que nunca estuvieron)
"""

import json
import argparse
import os
import sys
import getpass
from datetime import datetime
from collections import defaultdict

# Importar sistema de caché y tracker
from bc_cache_system import EmailCache, SyncTracker, get_embed_id

# Importar funciones del script de exportación
sys.path.insert(0, os.path.dirname(__file__))
from bc_imap_generator import (
    IMAPConfig,
    IMAPSessionManager,
    interactive_setup
)


def load_listened_from_browser(localStorage_file):
    """Lee el archivo JSON exportado del navegador"""
    try:
        with open(localStorage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        listened_by_genre = {}

        for key, value in data.items():
            if key.startswith('bandcamp_listened_'):
                genre = key.replace('bandcamp_listened_', '')

                if isinstance(value, list):
                    listened_by_genre[genre] = set(value)
                elif isinstance(value, str):
                    listened_by_genre[genre] = set(json.loads(value))

        return listened_by_genre

    except FileNotFoundError:
        print(f"⚠️  Archivo no encontrado: {localStorage_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al leer JSON: {e}")
        return {}


def load_existing_json(json_file):
    """Carga el JSON existente con la colección"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ℹ️  No existe {json_file}, se creará uno nuevo")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al leer {json_file}: {e}")
        return {}


def merge_collections_fixed(old_data, new_data, listened_by_genre, tracker):
    """
    Versión CORREGIDA de merge_collections

    Lógica:
    1. old_data = colección actual
    2. new_data = nuevos correos del IMAP
    3. listened_by_genre = álbumes que el usuario marcó como escuchados

    Proceso:
    A. Para cada álbum en old_data:
       - Si está en listened → ELIMINAR (usuario lo escuchó)
       - Si NO está en listened → MANTENER

    B. Para cada álbum en new_data:
       - Si YA existe en colección actual → SKIP (ya está)
       - Si fue eliminado previamente (tracker.was_removed) → SKIP (usuario no lo quiere)
       - Si es verdaderamente nuevo → AGREGAR

    Esto resuelve el problema de que los álbumes eliminados reaparecían.
    """
    merged = defaultdict(list)
    stats = {
        'removed': 0,
        'added': 0,
        'kept': 0,
        'skipped_previously_removed': 0,
        'by_genre': {}
    }

    all_genres = set(list(old_data.keys()) + list(new_data.keys()))

    for genre in all_genres:
        genre_stats = {
            'removed': 0,
            'added': 0,
            'kept': 0,
            'skipped': 0
        }

        old_embeds = old_data.get(genre, [])
        new_embeds = new_data.get(genre, [])
        listened_ids = listened_by_genre.get(genre, set())

        # PASO A: Procesar colección antigua
        kept_embeds = []
        existing_urls = set()

        for embed in old_embeds:
            embed_id = get_embed_id(embed['url'])

            if embed_id in listened_ids:
                # Usuario lo marcó como escuchado → ELIMINAR
                genre_stats['removed'] += 1

                # Marcar en tracker como eliminado
                tracker.mark_as_removed(genre, embed_id)
            else:
                # No está escuchado → MANTENER
                kept_embeds.append(embed)
                existing_urls.add(embed['url'])
                genre_stats['kept'] += 1

        # PASO B: Procesar nuevos del IMAP
        for embed in new_embeds:
            url = embed['url']
            embed_id = get_embed_id(url)

            # ¿Ya existe en la colección actual?
            if url in existing_urls:
                continue

            # ¿Fue eliminado previamente por el usuario?
            if tracker.was_removed(genre, embed_id):
                genre_stats['skipped'] += 1
                continue

            # Es verdaderamente NUEVO → AGREGAR
            kept_embeds.append(embed)
            existing_urls.add(url)
            genre_stats['added'] += 1

            # Marcar en tracker como agregado
            tracker.mark_as_added(genre, embed_id, url)

        # Solo incluir géneros con contenido
        if kept_embeds:
            merged[genre] = kept_embeds

        stats['by_genre'][genre] = genre_stats
        stats['removed'] += genre_stats['removed']
        stats['added'] += genre_stats['added']
        stats['kept'] += genre_stats['kept']
        stats['skipped_previously_removed'] += genre_stats['skipped']

    return dict(merged), stats


def export_new_emails_cached(config, folders, mark_as_read, include_read, cache, tracker):
    """Exporta nuevos correos usando caché"""
    try:
        from bc_export_to_json import process_imap_folder_cached

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

            embeds = process_imap_folder_cached(
                mail, folder_name, genre, config, cache, tracker,
                mark_as_read=mark_as_read,
                include_read=include_read
            )

            if genre not in embeds_by_genre:
                embeds_by_genre[genre] = []
            embeds_by_genre[genre].extend(embeds)

        return embeds_by_genre

    finally:
        session.disconnect()


def save_json(data, output_file):
    """Guarda los datos a JSON"""
    export_data = {}

    for genre, embeds in data.items():
        export_data[genre] = []
        for embed in embeds:
            embed_copy = embed.copy()

            # Convertir datetime a string
            if 'date_obj' in embed_copy:
                if isinstance(embed_copy['date_obj'], datetime):
                    embed_copy['date_obj'] = embed_copy['date_obj'].isoformat()
                else:
                    embed_copy['date_obj'] = None

            # Limpiar campos internos
            embed_copy.pop('processed_at', None)
            embed_copy.pop('cache_key', None)

            export_data[genre].append(embed_copy)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)


def print_stats(stats):
    """Imprime estadísticas CORREGIDAS de la sincronización"""
    print("\n" + "="*80)
    print("📊 ESTADÍSTICAS DE SINCRONIZACIÓN")
    print("="*80)
    print(f"\n✅ Álbumes mantenidos (no escuchados): {stats['kept']}")
    print(f"➕ Álbumes nuevos añadidos: {stats['added']}")
    print(f"➖ Álbumes eliminados (escuchados): {stats['removed']}")
    if stats['skipped_previously_removed'] > 0:
        print(f"⏭️  Álbumes ignorados (eliminados previamente): {stats['skipped_previously_removed']}")
    print(f"\n📦 Total final en colección: {stats['kept'] + stats['added']}")

    if stats['by_genre']:
        print("\n🔍 Por género:")
        for genre, genre_stats in sorted(stats['by_genre'].items()):
            total = genre_stats['kept'] + genre_stats['added']

            if total > 0 or genre_stats['removed'] > 0 or genre_stats['added'] > 0:
                print(f"\n  {genre}:")
                print(f"    • Mantenidos: {genre_stats['kept']}")
                print(f"    • Nuevos: {genre_stats['added']}")
                print(f"    • Eliminados: {genre_stats['removed']}")
                if genre_stats['skipped'] > 0:
                    print(f"    • Ignorados: {genre_stats['skipped']}")
                print(f"    • Total: {total}")


def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza tu colección de Bandcamp (VERSIÓN CORREGIDA)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flujo de trabajo CORREGIDO:
  1. Exporta localStorage desde tu navegador
  2. Ejecuta este script
  3. Los álbumes que marcaste como escuchados se ELIMINAN
  4. Los álbumes nuevos del correo se AGREGAN
  5. Los álbumes que eliminaste antes NO reaparecen
  6. Regenera el sitio

Ejemplos:
  # Sincronizar con caché
  python3 bc_sync_fixed.py --localStorage-file browser_data.json --interactive \\
    --folders "INBOX/Rock:Rock"

  # Solo eliminar escuchados (sin buscar nuevos)
  python3 bc_sync_fixed.py --localStorage-file browser_data.json --no-fetch
        """
    )

    # Opciones de localStorage
    parser.add_argument('--localStorage-file',
                       help='Archivo JSON con localStorage exportado')

    # Opciones de datos
    parser.add_argument('--input', default='bandcamp_data.json',
                       help='Archivo JSON actual')
    parser.add_argument('--output', default='bandcamp_data_synced.json',
                       help='Archivo JSON de salida')

    # Opciones de IMAP
    parser.add_argument('--no-fetch', action='store_true',
                       help='NO buscar nuevos correos')
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para IMAP')
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

    # Opciones de caché
    parser.add_argument('--cache-file', default='.bandcamp_cache.json',
                       help='Archivo de caché')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("🔄 SINCRONIZACIÓN DE COLECCIÓN BANDCAMP (VERSIÓN CORREGIDA)")
    print("="*80)
    print("\n✨ MEJORAS:")
    print("   • Los álbumes eliminados NO reaparecen")
    print("   • Usa caché para procesar más rápido")
    print("   • Tracking preciso de cambios")
    print()

    # Inicializar cache y tracker
    cache = EmailCache(args.cache_file)
    tracker = SyncTracker()

    # Cargar localStorage si se proporciona
    listened_by_genre = {}
    if args.localStorage_file:
        print(f"📥 Cargando localStorage desde: {args.localStorage_file}")
        listened_by_genre = load_listened_from_browser(args.localStorage_file)

        if listened_by_genre:
            total_listened = sum(len(ids) for ids in listened_by_genre.values())
            print(f"✓ {total_listened} álbumes marcados como escuchados")
            for genre, ids in listened_by_genre.items():
                print(f"  • {genre}: {ids} escuchados")
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
        new_data = export_new_emails_cached(
            config, args.folders, mark_as_read, args.include_read, cache, tracker
        )

        if new_data:
            total_new = sum(len(embeds) for embeds in new_data.values())
            print(f"✓ {total_new} álbumes encontrados en correos")
        else:
            print("ℹ️  No se encontraron nuevos álbumes")
    else:
        print("\n⏭️  Saltando búsqueda de nuevos correos (--no-fetch)")

    # Fusionar colecciones CON LÓGICA CORREGIDA
    print("\n🔄 Sincronizando con lógica corregida...")
    merged_data, stats = merge_collections_fixed(old_data, new_data, listened_by_genre, tracker)

    # Guardar resultado
    save_json(merged_data, args.output)
    print(f"\n✅ Colección sincronizada guardada en: {args.output}")

    # Guardar tracker
    tracker.save()
    print(f"✅ Tracker actualizado: .bandcamp_sync_tracker.json")

    # Mostrar estadísticas
    print_stats(stats)

    print("\n" + "="*80)
    print("✅ SINCRONIZACIÓN COMPLETADA")
    print("="*80)

    print("\n📁 PRÓXIMOS PASOS:")
    print(f"   1. Revisa el archivo: {args.output}")
    print(f"   2. Regenera el sitio:")
    print(f"      python3 bc_static_generator.py --input {args.output}")
    print(f"   3. Sube los cambios a GitHub")
    print()

    if stats['skipped_previously_removed'] > 0:
        print("ℹ️  NOTA:")
        print(f"   Se ignoraron {stats['skipped_previously_removed']} álbumes que habías")
        print("   eliminado previamente. Esto es correcto - no reaparecerán.")
        print()


if __name__ == '__main__':
    main()
