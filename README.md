# 🎵 Bandcamp Collection para GitHub Pages

Convierte tus correos de Bandcamp en una colección web estática que puedes hostear gratis en GitHub Pages, con la capacidad de marcar álbumes como "escuchados" sin necesidad de backend.

## 🌟 Características

- ✅ **100% estático** - No necesita servidor backend
- 💾 **Persistencia local** - Los álbumes escuchados se guardan en localStorage
- 🎨 **Diseño moderno** - Interfaz bonita y responsive
- 📱 **Mobile-friendly** - Funciona perfecto en móviles
- 🆓 **Gratis** - Hostea en GitHub Pages sin costo
- 🔒 **Privado** - Tus datos nunca salen de tu navegador

## 📦 Archivos

- `bc_export_to_json.py` - Exporta correos IMAP a JSON
- `bc_static_generator.py` - Genera el sitio estático desde JSON
- `bc_imap_generator.py` - Script original (necesario para la exportación)

## 🚀 Guía Rápida

### Paso 1: Exportar datos desde tu correo

```bash
# Modo interactivo (recomendado)
python3 bc_export_to_json.py --interactive --folders "INBOX/Rock:Rock" "INBOX/Electronic:Electronic"

# O modo directo
python3 bc_export_to_json.py \
  --server imap.gmail.com \
  --email tu@email.com \
  --folders "INBOX/Rock:Rock" "INBOX/Jazz:Jazz" \
  --output bandcamp_data.json
```

**Opciones útiles:**

- `--include-read` - Incluir correos ya leídos
- `--no-mark-read` - NO marcar correos como leídos
- `--output archivo.json` - Cambiar nombre del archivo de salida

### Paso 2: Generar sitio estático

```bash
python3 bc_static_generator.py --input bandcamp_data.json
```

Esto creará un directorio `docs/` con todos los archivos HTML.

**Opciones:**

- `--output-dir nombre` - Cambiar directorio de salida (default: `docs`)
- `--items-per-page 15` - Cambiar número de álbumes por página

### Paso 3: Subir a GitHub

1. **Crea un repositorio en GitHub** (público o privado)

2. **Inicializa Git en tu directorio:**

   ```bash
   git init
   git add docs/
   git commit -m "Initial commit: Bandcamp collection"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   git push -u origin main
   ```

3. **Activa GitHub Pages:**
   - Ve a tu repositorio en GitHub
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/docs`
   - Save

4. **¡Listo!** Tu sitio estará disponible en:
   `https://tu-usuario.github.io/tu-repo/`

## 🎯 Uso del sitio web

### Marcar como escuchado

- Click en "🎧 Marcar como escuchado"
- El álbum desaparecerá con una animación
- Se guarda en localStorage de tu navegador
- La próxima vez que visites la página, seguirá oculto

### Restaurar álbumes

- Click en "🔄 Restaurar todos" en cualquier género
- Todos los álbumes reaparecerán
- Útil si quieres revisar tu colección de nuevo

### Estadísticas

Cada página de género muestra:

- Total de discos
- Discos escuchados
- Discos pendientes

## 🔧 Personalización

### Cambiar colores

Edita el gradiente en el CSS de `bc_static_generator.py`:

```python
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Cambiar discos por página

```bash
python3 bc_static_generator.py --input data.json --items-per-page 20
```

### Estructura de directorios personalizada

```bash
python3 bc_static_generator.py --input data.json --output-dir mi-sitio
```

## 📝 Formato del JSON

El archivo `bandcamp_data.json` tiene esta estructura:

```json
{
  "Rock": [
    {
      "url": "https://artist.bandcamp.com/album/name",
      "embed": "<iframe ...></iframe>",
      "subject": "Nombre del álbum",
      "date": "Mon, 01 Jan 2024 12:00:00 +0000",
      "sender": "artist@bandcamp.com"
    }
  ],
  "Electronic": [...]
}
```

Puedes editar este archivo manualmente si quieres agregar o quitar álbumes.

## 🔄 Actualizar tu colección

Para agregar nuevos álbumes:

1. Exporta de nuevo desde tu correo:

   ```bash
   python3 bc_export_to_json.py --interactive --folders "INBOX/Rock:Rock"
   ```

2. Regenera el sitio:

   ```bash
   python3 bc_static_generator.py --input bandcamp_data.json
   ```

3. Sube los cambios:
   ```bash
   git add docs/
   git commit -m "Update: New albums"
   git push
   ```

GitHub Pages se actualizará automáticamente en unos minutos.

## 💡 Consejos

### Gmail

Si usas Gmail, necesitas una "Contraseña de aplicación":

1. Ve a tu cuenta de Google
2. Seguridad → Verificación en 2 pasos (actívala si no lo está)
3. Contraseñas de aplicaciones
4. Crea una para "Correo"
5. Usa esa contraseña en lugar de tu contraseña normal

### Organización por carpetas

Crea carpetas en tu correo para cada género:

- `INBOX/Rock`
- `INBOX/Electronic`
- `INBOX/Jazz`

Luego exporta:

```bash
python3 bc_export_to_json.py --interactive \
  --folders "INBOX/Rock:Rock" "INBOX/Electronic:Electronic" "INBOX/Jazz:Jazz"
```

### Privacidad

- El código es 100% cliente-side
- Tus datos nunca se envían a ningún servidor
- localStorage es local a tu navegador
- Puedes hacer el repo privado si quieres

### Rendimiento

- Cada género es una página separada
- La paginación mejora la carga con muchos álbumes
- Los iframes de Bandcamp se cargan de forma lazy

## 🐛 Solución de problemas

### "No se encontró el módulo bc_imap_generator"

Asegúrate de que los 3 scripts estén en el mismo directorio.

### "Error de autenticación IMAP"

- Verifica tu usuario y contraseña
- Si usas Gmail, necesitas una contraseña de aplicación
- Revisa que IMAP esté activado en tu cuenta

### Los álbumes no desaparecen

- Verifica que JavaScript esté habilitado
- Abre la consola del navegador para ver errores
- Intenta en modo incógnito (puede ser una extensión bloqueando localStorage)

### GitHub Pages no se actualiza

- Espera 2-5 minutos después de hacer push
- Verifica que la configuración de Pages esté correcta
- Revisa que los archivos estén en la carpeta correcta

## 🎨 Capturas

El sitio incluye:

- **Índice principal** - Lista de todos los géneros con contadores
- **Páginas de género** - Grid de álbumes con embeds de Bandcamp
- **Paginación** - Para colecciones grandes
- **Estadísticas** - Seguimiento de progreso
- **Diseño moderno** - Gradientes, sombras, animaciones

## 📄 Licencia

Libre para uso personal. Los datos de Bandcamp pertenecen a sus respectivos artistas.

## 🤝 Contribuciones

¿Ideas para mejorar? ¡Abre un issue o pull request!

## 🙏 Créditos

- Embeds cortesía de Bandcamp
- Inspirado en coleccionistas de música de todo el mundo

---

**¿Preguntas?** Abre un issue en el repositorio.

**¿Te gusta?** ¡Dale una estrella ⭐!
