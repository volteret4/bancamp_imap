#!/usr/bin/env python3
"""
Script para exportar embeds de Bandcamp desde IMAP a JSON
Para luego generar un sitio estático con bc_static_generator.py
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
    process_imap_folder
)
import argparse
import getpass


def export_to_json(embeds_by_genre, output_file):
    """
    Exporta los embeds a un archivo JSON.
    """
    # Preparar datos para JSON (convertir datetime a string)
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

            export_data[genre].append(embed_copy)

    # Guardar a JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Datos exportados a: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Exporta embeds de Bandcamp desde IMAP a JSON'
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

    args = parser.parse_args()

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
        print(f"📧 EXPORTANDO CORREOS A JSON")
        print(f"{'='*80}")
        print(f"Servidor: {config.server}")
        print(f"Email: {config.email}")
        print(f"Marcar como leídos: {'Sí' if mark_as_read else 'No'}")
        print(f"Incluir ya leídos: {'Sí' if include_read else 'No'}")
        print(f"{'='*80}\n")

        for folder_spec in args.folders:
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

        # Exportar a JSON
        total_embeds = sum(len(embeds) for embeds in embeds_by_genre.values())

        print(f"\n{'='*80}")
        print(f"📊 RESUMEN")
        print(f"{'='*80}")
        print(f"Total de embeds encontrados: {total_embeds}")
        print(f"Géneros: {len(embeds_by_genre)}")

        if total_embeds > 0:
            export_to_json(embeds_by_genre, args.output)

            print(f"\n{'='*80}")
            print(f"✅ EXPORTACIÓN COMPLETADA")
            print(f"{'='*80}\n")
            print(f"📝 PRÓXIMOS PASOS:")
            print(f"   1. Genera el sitio estático:")
            print(f"      python3 bc_static_generator.py --input {args.output}")
            print(f"   2. Sube el directorio 'docs' a GitHub")
            print(f"   3. Activa GitHub Pages")
            print()
        else:
            print("\n⚠️  No se encontraron embeds de Bandcamp en los correos")

    finally:
        # Cerrar sesión
        session.disconnect()
        print("\n✓ Sesión IMAP cerrada")


if __name__ == '__main__':
    main()
