#!/usr/bin/env python3
"""
Script para exportar embeds de Bandcamp desde IMAP a JSON
VERSIÓN MEJORADA con sistema de caché
- Evita procesar correos duplicados
- Soporta múltiples cuentas y carpetas
- Mucho más rápido en ejecuciones subsecuentes
"""

import json
import sys
import os
from datetime import datetime

# Importar sistema de caché
from bc_cache_system import EmailCache, SyncTracker, get_embed_id

# Importar funciones del script original
sys.path.insert(0, os.path.dirname(__file__))
from bc_imap_generator import (
    IMAPConfig,
    IMAPSessionManager,
    interactive_setup,
    decode_mime_header,
    get_email_body,
    extract_bandcamp_link,
    get_bandcamp_embed
)
import argparse
import getpass
from email.utils import parsedate_to_datetime


def process_imap_folder_cached(mail, folder_name, genre, config, cache, tracker,
                                mark_as_read=True, include_read=False):
    """
    Versión mejorada de process_imap_folder que usa caché.
    Solo procesa correos que no están en caché.
    """
    embeds = []

    print(f"\n{'='*80}")
    print(f"📂 Procesando carpeta: {folder_name}")
    print(f"🎵 Género: {genre}")
    print(f"{'='*80}\n")

    try:
        # Seleccionar la carpeta
        status, messages = mail.select(f'"{folder_name}"', readonly=False)

        if status != 'OK':
            print(f"❌ No se pudo acceder a la carpeta {folder_name}")
            return embeds

        num_messages = int(messages[0])
        print(f"📧 Correos en la carpeta: {num_messages}")

        if num_messages == 0:
            print("ℹ️  Carpeta vacía")
            return embeds

        # Buscar correos según parámetro
        if include_read:
            status, messages = mail.search(None, 'ALL')
            print(f"🔍 Buscando TODOS los correos...")
        else:
            status, messages = mail.search(None, 'UNSEEN')
            print(f"🔍 Buscando solo correos NO LEÍDOS...")

        if status != 'OK':
            print("❌ Error al buscar correos")
            return embeds

        email_ids = messages[0].split()
        print(f"📨 Encontrados {len(email_ids)} correos candidatos")

        if len(email_ids) == 0:
            print("ℹ️  No hay correos que procesar")
            return embeds

        # Contadores para estadísticas
        cached_count = 0
        processed_count = 0
        failed_count = 0

        for i, email_id in enumerate(email_ids, 1):
            try:
                # Obtener headers primero (más rápido)
                status, msg_data = mail.fetch(email_id, '(BODY.PEEK[HEADER])')

                if status != 'OK':
                    continue

                # Parsear headers
                import email
                header_data = msg_data[0][1]
                msg_headers = email.message_from_bytes(header_data)

                message_id = msg_headers.get('Message-ID', '')
                subject = decode_mime_header(msg_headers.get('Subject', ''))
                sender = decode_mime_header(msg_headers.get('From', ''))
                date = msg_headers.get('Date', '')

                if not message_id:
                    # Sin Message-ID, generar uno basado en subject+date
                    message_id = f"generated_{abs(hash(subject + date))}"

                # VERIFICAR CACHÉ
                cache_key_parts = (config.server, config.email, folder_name, message_id)

                if cache.has(*cache_key_parts):
                    cached_entry = cache.get(*cache_key_parts)

                    print(f"  [{i}/{len(email_ids)}] ⚡ CACHÉ: {subject[:50]}")

                    # Usar datos del caché
                    embeds.append(cached_entry)
                    cached_count += 1

                    # Marcar como leído si se solicita
                    if mark_as_read:
                        mail.store(email_id, '+FLAGS', '\\Seen')

                    continue

                # NO ESTÁ EN CACHÉ - Procesar normalmente
                print(f"  [{i}/{len(email_ids)}] 🆕 NUEVO: {subject[:50]}")

                # Obtener cuerpo completo
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    failed_count += 1
                    continue

                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)

                # Parsear fecha para ordenamiento
                try:
                    date_obj = parsedate_to_datetime(date) if date else None
                except:
                    date_obj = None

                # Extraer contenido
                email_content = get_email_body(msg)

                if not email_content:
                    print("       ⚠️  Sin contenido")
                    failed_count += 1
                    continue

                # Buscar enlace de Bandcamp
                bandcamp_link = extract_bandcamp_link(email_content)

                if not bandcamp_link:
                    print("       • Sin enlaces de Bandcamp")
                    failed_count += 1
                    continue

                print(f"       ✓ Enlace encontrado!")

                # Obtener embed
                embed_code = get_bandcamp_embed(bandcamp_link)

                if not embed_code:
                    print(f"       ⚠️  No se pudo obtener el embed")
                    failed_count += 1
                    continue

                email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)

                embed_data = {
                    'url': bandcamp_link,
                    'embed': embed_code,
                    'subject': subject,
                    'date': date,
                    'date_obj': date_obj,
                    'sender': sender,
                    'email_id': email_id_str,
                    'message_id': message_id,
                    'folder': folder_name,
                    'genre': genre
                }

                embeds.append(embed_data)
                processed_count += 1

                # AGREGAR AL CACHÉ
                cache.add(*cache_key_parts, embed_data)

                # AGREGAR AL TRACKER
                embed_id = get_embed_id(bandcamp_link)
                tracker.mark_as_added(genre, embed_id, bandcamp_link)

                print(f"       ✓ Embed procesado y cacheado")

                # Marcar como leído si se encontró un enlace
                if mark_as_read:
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"       📖 Marcado como leído")

            except Exception as e:
                print(f"       ❌ Error procesando correo: {e}")
                failed_count += 1
                continue

        # Guardar caché y tracker
        cache.save()
        tracker.save()

        print(f"\n{'='*80}")
        print(f"📊 ESTADÍSTICAS DE PROCESAMIENTO")
        print(f"{'='*80}")
        print(f"  ⚡ Desde caché:  {cached_count}")
        print(f"  🆕 Procesados:   {processed_count}")
        print(f"  ❌ Fallidos:     {failed_count}")
        print(f"  ✅ Total:        {len(embeds)} embeds")
        print(f"{'='*80}\n")

        # Ordenar por fecha (más reciente primero)
        embeds.sort(key=lambda x: x.get('date_obj') or datetime.min, reverse=True)

    except Exception as e:
        print(f"❌ Error al procesar carpeta {folder_name}: {e}")

    return embeds


def export_to_json(embeds_by_genre, output_file):
    """Exporta los embeds a un archivo JSON"""
    export_data = {}

    for genre, embeds in embeds_by_genre.items():
        export_data[genre] = []
        for embed in embeds:
            embed_copy = embed.copy()

            # Convertir datetime a string para JSON
            if 'date_obj' in embed_copy:
                if isinstance(embed_copy['date_obj'], datetime):
                    embed_copy['date_obj'] = embed_copy['date_obj'].isoformat()
                else:
                    embed_copy['date_obj'] = None

            # Limpiar campos internos de caché
            embed_copy.pop('processed_at', None)
            embed_copy.pop('cache_key', None)

            export_data[genre].append(embed_copy)

    # Guardar a JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Datos exportados a: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Exporta embeds de Bandcamp desde IMAP a JSON (CON CACHÉ)'
    )

    # Opciones de conexión
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para configurar la conexión')
    parser.add_argument('--server', help='Servidor IMAP')
    parser.add_argument('--port', type=int, default=993)
    parser.add_argument('--email', help='Dirección de email')
    parser.add_argument('--password', help='Contraseña')

    # Opciones de operación
    parser.add_argument('--folders', nargs='+', required=True,
                       help='Carpetas en formato "ruta:género"')
    parser.add_argument('--no-mark-read', action='store_true',
                       help='NO marcar los correos como leídos')
    parser.add_argument('--include-read', action='store_true',
                       help='Incluir correos ya leídos')

    # Opciones de caché
    parser.add_argument('--no-cache', action='store_true',
                       help='NO usar caché (procesar todo desde cero)')
    parser.add_argument('--cache-file', default='.bandcamp_cache.json',
                       help='Archivo de caché (default: .bandcamp_cache.json)')
    parser.add_argument('--clean-cache', type=int, metavar='DAYS',
                       help='Limpiar entradas de caché más antiguas de N días')
    parser.add_argument('--show-cache-stats', action='store_true',
                       help='Mostrar estadísticas del caché y salir')

    # Opciones de salida
    parser.add_argument('--output', default='bandcamp_data.json',
                       help='Archivo JSON de salida')

    args = parser.parse_args()

    # Inicializar caché y tracker
    cache = EmailCache(args.cache_file) if not args.no_cache else None
    tracker = SyncTracker()

    # Mostrar stats de caché si se solicita
    if args.show_cache_stats:
        if cache:
            stats = cache.get_stats()
            print("\n📊 ESTADÍSTICAS DEL CACHÉ")
            print("="*50)
            print(f"  Total correos cacheados: {stats['total_emails']}")
            print(f"  Servidores diferentes:   {stats['servers']}")
            print(f"  Cuentas diferentes:      {stats['accounts']}")
            print(f"  Carpetas diferentes:     {stats['folders']}")
            print("="*50)
        else:
            print("ℹ️  Caché deshabilitado (usa sin --no-cache)")
        return

    # Limpiar caché si se solicita
    if args.clean_cache and cache:
        print(f"\n🗑️  Limpiando entradas de caché > {args.clean_cache} días...")
        removed = cache.clean_old_entries(args.clean_cache)
        if removed == 0:
            print("  ℹ️  No hay entradas antiguas para limpiar")
        return

    # Configurar conexión IMAP
    if args.interactive:
        config = interactive_setup()
    elif args.server and args.email:
        password = args.password or getpass.getpass(f"Contraseña para {args.email}: ")
        config = IMAPConfig(args.server, args.port, args.email, password)
    else:
        print("❌ Debes usar --interactive o proporcionar --server y --email")
        return

    # Conectar al servidor IMAP
    try:
        session = IMAPSessionManager.get_instance()
        mail = session.connect(config)
    except Exception as e:
        print(f"\n❌ No se pudo conectar al servidor IMAP")
        print(f"Error: {e}")
        return

    try:
        embeds_by_genre = {}
        mark_as_read = not args.no_mark_read
        include_read = args.include_read

        print(f"\n{'='*80}")
        print(f"📧 EXPORTANDO CORREOS A JSON {'(CON CACHÉ)' if cache else '(SIN CACHÉ)'}")
        print(f"{'='*80}")
        print(f"Servidor: {config.server}")
        print(f"Email: {config.email}")
        print(f"Marcar como leídos: {'Sí' if mark_as_read else 'No'}")
        print(f"Incluir ya leídos: {'Sí' if include_read else 'No'}")
        if cache:
            stats = cache.get_stats()
            print(f"Correos en caché: {stats['total_emails']}")
        print(f"{'='*80}\n")

        for folder_spec in args.folders:
            if ':' in folder_spec:
                folder_name, genre = folder_spec.rsplit(':', 1)
            else:
                folder_name = folder_spec
                genre = folder_name.split('/')[-1]

            if cache:
                embeds = process_imap_folder_cached(
                    mail, folder_name, genre, config, cache, tracker,
                    mark_as_read=mark_as_read,
                    include_read=include_read
                )
            else:
                # Usar método original sin caché
                from bc_imap_generator import process_imap_folder
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

        # Exportar a JSON
        total_embeds = sum(len(embeds) for embeds in embeds_by_genre.values())

        print(f"\n{'='*80}")
        print(f"📊 RESUMEN FINAL")
        print(f"{'='*80}")
        print(f"Total de embeds encontrados: {total_embeds}")
        print(f"Géneros: {len(embeds_by_genre)}")

        if total_embeds > 0:
            export_to_json(embeds_by_genre, args.output)

            print(f"\n{'='*80}")
            print(f"✅ EXPORTACIÓN COMPLETADA")
            print(f"{'='*80}\n")
            print(f"📁 PRÓXIMOS PASOS:")
            print(f"   1. Genera el sitio estático:")
            print(f"      python3 bc_static_generator.py --input {args.output}")
            print(f"   2. Sube el directorio 'docs' a GitHub")
            print(f"   3. Activa GitHub Pages")

            if cache:
                stats = cache.get_stats()
                print(f"\n💾 CACHÉ ACTUALIZADO:")
                print(f"   Total correos: {stats['total_emails']}")
                print(f"   Archivo: {args.cache_file}")
            print()
        else:
            print("\n⚠️  No se encontraron embeds de Bandcamp en los correos")

    finally:
        # Cerrar sesión
        session.disconnect()
        print("\n✓ Sesión IMAP cerrada")


if __name__ == '__main__':
    main()
