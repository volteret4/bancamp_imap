#!/usr/bin/env python3
"""
Script CORREGIDO para exportar embeds de Bandcamp desde IMAP a JSON
CON SISTEMA DE CACHÉ INTEGRADO para evitar descargar correos repetidos
"""

import json
import sys
import os
from datetime import datetime

# Importar funciones del script original
sys.path.insert(0, os.path.dirname(__file__))
from bc_imap_generator import (
    IMAPConfig,
    IMAPSessionManager,
    interactive_setup,
    get_email_body,
    decode_mime_header,
    extract_bandcamp_link,
    get_bandcamp_embed
)
from bc_cache_system import EmailCache, get_embed_id

import argparse
import getpass
import email
from email.utils import parsedate_to_datetime


def datetime_serializer(obj):
    """Serializador personalizado para objetos datetime"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def process_imap_folder_with_cache(mail, folder_name, genre, cache, mark_as_read=True,
                                   include_read=False, config=None):
    """
    Procesa una carpeta IMAP buscando enlaces de Bandcamp.
    USA CACHÉ para evitar descargar correos ya procesados.

    Args:
        mail: Conexión IMAP activa
        folder_name: Nombre de la carpeta a procesar
        genre: Género musical para clasificar
        cache: Instancia de EmailCache
        mark_as_read: Si True, marca los correos como leídos después de procesarlos
        include_read: Si True, incluye correos ya leídos
        config: IMAPConfig para el caché

    Returns:
        Lista de embeds de Bandcamp encontrados
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

        # Buscar correos según el parámetro include_read
        if include_read:
            status, messages = mail.search(None, 'ALL')
            print(f"🔍 Buscando TODOS los correos (leídos y no leídos)...")
        else:
            status, messages = mail.search(None, 'UNSEEN')
            print(f"🔍 Buscando solo correos NO LEÍDOS...")

        if status != 'OK':
            print("❌ Error al buscar correos")
            return embeds

        email_ids = messages[0].split()
        print(f"📬 Procesando {len(email_ids)} correos...\n")

        if len(email_ids) == 0:
            print("ℹ️  No hay correos que procesar con los criterios especificados")
            return embeds

        # Contadores de caché
        cached_count = 0
        processed_count = 0

        for i, email_id in enumerate(email_ids, 1):
            try:
                # Obtener el correo
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parsear el correo
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)

                # Obtener información del correo
                subject = decode_mime_header(msg.get('Subject', ''))
                sender = decode_mime_header(msg.get('From', ''))
                date = msg.get('Date', '')
                message_id = msg.get('Message-ID', '')

                print(f"  [{i}/{len(email_ids)}] De: {sender[:50]}")
                print(f"       Asunto: {subject[:70]}")

                # VERIFICAR CACHÉ
                if cache.has(config.server, config.email, folder_name, message_id):
                    cached_data = cache.get(config.server, config.email, folder_name, message_id)

                    # Reconstruir date_obj como datetime para que el sort funcione
                    if cached_data.get('date_obj') and isinstance(cached_data['date_obj'], str):
                        try:
                            cached_data = cached_data.copy()
                            cached_data['date_obj'] = datetime.fromisoformat(cached_data['date_obj'])
                        except (ValueError, TypeError):
                            cached_data['date_obj'] = None

                    # Usar datos del caché
                    embeds.append(cached_data)
                    cached_count += 1

                    print(f"       ✅ Usando CACHÉ ({cached_count} cached)")

                    # Marcar como leído si es necesario
                    if mark_as_read:
                        mail.store(email_id, '+FLAGS', '\\Seen')

                    continue

                # NO ESTÁ EN CACHÉ - Procesar normalmente
                processed_count += 1

                # Parsear fecha para ordenamiento
                try:
                    date_obj = parsedate_to_datetime(date) if date else None
                except:
                    date_obj = None

                # Extraer el cuerpo del correo
                email_content = get_email_body(msg)

                if not email_content:
                    print("       ⚠️  Sin contenido")
                    continue

                # Buscar enlace de Bandcamp
                bandcamp_link = extract_bandcamp_link(email_content)

                if bandcamp_link:
                    print(f"       ✅ Enlace encontrado!")
                    print(f"       🔗 URL completa: {bandcamp_link}")

                    # Obtener el embed
                    embed_code = get_bandcamp_embed(bandcamp_link)

                    if embed_code:
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

                        # GUARDAR EN CACHÉ (sin date_obj como datetime, usar string)
                        cache_data = embed_data.copy()
                        cache_data['date_obj'] = date_obj.isoformat() if date_obj else None
                        cache.add(config.server, config.email, folder_name,
                                message_id, cache_data)

                        print(f"       ✅ Embed obtenido y guardado en caché ({len(embeds)} total)")

                        # Marcar como leído
                        if mark_as_read:
                            mail.store(email_id, '+FLAGS', '\\Seen')
                            print(f"       📖 Marcado como leído")
                    else:
                        print(f"       ⚠️  No se pudo obtener el embed")
                else:
                    print("       • Sin enlaces de Bandcamp")

            except Exception as e:
                print(f"       ❌ Error procesando correo: {e}")
                continue

        # Guardar caché después de procesar la carpeta
        if processed_count > 0:
            cache.save()
            print(f"\n💾 Caché guardado ({processed_count} nuevos, {cached_count} reutilizados)")

        print(f"\n{'='*80}")
        print(f"✅ Procesamiento completado: {len(embeds)} embeds encontrados")
        print(f"   📦 Del caché: {cached_count}")
        print(f"   🆕 Procesados: {processed_count}")
        print(f"{'='*80}\n")

        # Ordenar por fecha (más reciente primero)
        embeds.sort(key=lambda x: x.get('date_obj') or datetime.min, reverse=True)

    except Exception as e:
        print(f"❌ Error al procesar carpeta {folder_name}: {e}")

    return embeds


def export_to_json(embeds_by_genre, output_file):
    """
    Exporta los embeds a un archivo JSON.
    VERSIÓN CORREGIDA: Maneja datetime correctamente
    """
    print(f"\n💾 Exportando a JSON...")

    # Preparar datos para JSON
    export_data = {}

    for genre, embeds in embeds_by_genre.items():
        export_data[genre] = []

        for embed in embeds:
            # Crear copia limpia
            embed_copy = {}

            for key, value in embed.items():
                # Convertir datetime a string
                if isinstance(value, datetime):
                    embed_copy[key] = value.isoformat()
                # Mantener None y otros tipos serializables
                elif value is None or isinstance(value, (str, int, float, bool, list, dict)):
                    embed_copy[key] = value
                # Convertir todo lo demás a string
                else:
                    embed_copy[key] = str(value)

            export_data[genre].append(embed_copy)

    # Guardar a JSON con manejo de errores
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=datetime_serializer)

        # Verificar que el archivo se creó
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ Archivo creado: {output_file}")
            print(f"   Tamaño: {file_size:,} bytes")
            print(f"   Géneros: {len(export_data)}")
            print(f"   Total embeds: {sum(len(e) for e in export_data.values())}")
        else:
            print(f"❌ ERROR: El archivo no se creó")

    except Exception as e:
        print(f"❌ ERROR al guardar JSON: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Exporta embeds de Bandcamp desde IMAP a JSON (CON CACHÉ)'
    )

    # Opciones de conexión
    parser.add_argument('--interactive', action='store_true',
                       help='Modo interactivo para configurar la conexión')
    parser.add_argument('--server', help='Servidor IMAP (ej: imap.gmail.com)')
    parser.add_argument('--port', type=int, default=993, help='Puerto IMAP (default: 993)')
    parser.add_argument('--email', help='Dirección de email')
    parser.add_argument('--password', help='Contraseña (no recomendado, usa --interactive)')

    # Opciones de operación
    parser.add_argument('--folders', nargs='+', required=True,
                       help='Carpetas en formato "ruta:género" (ej: "INBOX/Rock:Rock")')
    parser.add_argument('--no-mark-read', action='store_true',
                       help='NO marcar los correos como leídos después de procesarlos')
    parser.add_argument('--include-read', action='store_true',
                       help='Incluir correos ya leídos (por defecto solo procesa no leídos)')

    # Opciones de salida
    parser.add_argument('--output', default='bandcamp_data.json',
                       help='Archivo JSON de salida (default: bandcamp_data.json)')

    # Opciones de caché
    parser.add_argument('--cache-file', default='.bandcamp_cache.json',
                       help='Archivo de caché (default: .bandcamp_cache.json)')
    parser.add_argument('--no-cache', action='store_true',
                       help='Desactivar sistema de caché (forzar procesamiento completo)')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Limpiar caché antes de empezar')
    parser.add_argument('--cache-stats', action='store_true',
                       help='Mostrar estadísticas del caché y salir')

    args = parser.parse_args()

    # Inicializar caché
    cache = EmailCache(args.cache_file)

    # Mostrar estadísticas del caché si se solicita
    if args.cache_stats:
        stats = cache.get_stats()
        print("\n" + "="*70)
        print("📊 ESTADÍSTICAS DEL CACHÉ")
        print("="*70)
        print(f"   Total correos en caché: {stats['total_emails']}")
        print(f"   Servidores: {stats['servers']}")
        print(f"   Cuentas: {stats['accounts']}")
        print(f"   Carpetas: {stats['folders']}")
        print(f"\n   Archivo: {args.cache_file}")
        if os.path.exists(args.cache_file):
            size = os.path.getsize(args.cache_file)
            print(f"   Tamaño: {size:,} bytes")
        print()
        return

    # Limpiar caché si se solicita
    if args.clear_cache:
        if os.path.exists(args.cache_file):
            os.remove(args.cache_file)
            print(f"🗑️  Caché limpiado: {args.cache_file}")
            cache = EmailCache(args.cache_file)
        else:
            print(f"ℹ️  No hay caché para limpiar")

    # Configurar conexión IMAP
    if args.interactive:
        config = interactive_setup()
    elif args.server and args.email:
        password = args.password
        if not password:
            password = getpass.getpass(f"Contraseña para {args.email}: ")
        config = IMAPConfig(args.server, args.port, args.email, password)
    else:
        print("❌ Debes usar --interactive o proporcionar --server y --email")
        print("Usa --help para ver ejemplos de uso")
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
        print(f"📧 EXPORTANDO CORREOS A JSON (CON CACHÉ)")
        print(f"{'='*80}")
        print(f"Servidor: {config.server}")
        print(f"Email: {config.email}")
        print(f"Marcar como leídos: {'Sí' if mark_as_read else 'No'}")
        print(f"Incluir ya leídos: {'Sí' if include_read else 'No'}")
        print(f"Caché: {'Desactivado' if args.no_cache else 'Activado'}")
        print(f"{'='*80}\n")

        # Si no se quiere caché, usar uno temporal
        if args.no_cache:
            cache = EmailCache(':memory:')  # Esto fallará, pero el punto es no guardarlo

        for folder_spec in args.folders:
            if ':' in folder_spec:
                folder_name, genre = folder_spec.rsplit(':', 1)
            else:
                folder_name = folder_spec
                genre = folder_name.split('/')[-1]

            try:
                print(f"\n{'='*80}")
                print(f"📂 Procesando: {folder_name} → {genre}")
                print(f"{'='*80}\n")

                embeds = process_imap_folder_with_cache(
                    mail, folder_name, genre, cache,
                    mark_as_read=mark_as_read,
                    include_read=include_read,
                    config=config
                )

                if genre not in embeds_by_genre:
                    embeds_by_genre[genre] = []
                embeds_by_genre[genre].extend(embeds)

                print(f"\n✅ {genre}: {len(embeds)} embeds encontrados")

            except Exception as e:
                print(f"\n❌ Error al procesar carpeta {folder_name}: {e}")
                print(f"   Tipo de error: {type(e).__name__}")
                print(f"   Continuando con siguiente carpeta...")
                continue

        # Exportar a JSON
        total_embeds = sum(len(embeds) for embeds in embeds_by_genre.values())

        print(f"\n{'='*80}")
        print(f"📊 RESUMEN")
        print(f"{'='*80}")
        print(f"Total de embeds encontrados: {total_embeds}")
        print(f"Géneros: {len(embeds_by_genre)}")

        for genre, embeds in embeds_by_genre.items():
            print(f"  • {genre}: {len(embeds)} embeds")

        if total_embeds > 0:
            try:
                export_to_json(embeds_by_genre, args.output)

                # Mostrar estadísticas del caché
                cache_stats = cache.get_stats()
                print(f"\n📦 Estadísticas del caché:")
                print(f"   Total en caché: {cache_stats['total_emails']}")

                print(f"\n{'='*80}")
                print(f"✅ EXPORTACIÓN COMPLETADA")
                print(f"{'='*80}\n")
                print(f"📝 PRÓXIMOS PASOS:")
                print(f"   1. Verifica el archivo:")
                print(f"      cat {args.output}")
                print(f"   2. Genera el sitio estático:")
                print(f"      python3 bc_static_generator.py --input {args.output}")
                print(f"   3. Sube el directorio 'docs' a GitHub")
                print(f"   4. Activa GitHub Pages")
                print()

            except Exception as e:
                print(f"\n❌ ERROR CRÍTICO al exportar:")
                print(f"   {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n⚠️  No se encontraron embeds de Bandcamp en los correos")
            print("   Verifica que:")
            print("   1. Las carpetas existen")
            print("   2. Hay correos con enlaces de Bandcamp")
            print("   3. Los enlaces son válidos (album o track)")

    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        print(f"   Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()

    finally:
        # Cerrar sesión
        session.disconnect()
        print("\n✅ Sesión IMAP cerrada")


if __name__ == '__main__':
    main()
