# 🎵 Bandcamp Collection para GitHub Pages

Convierte tus correos de Bandcamp en una colección web estática que puedes hostear gratis en GitHub Pages, con la capacidad de marcar álbumes como "escuchados" sin necesidad de backend.

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

# 🔄 Guía de Sincronización

## ¿Para qué sirve la sincronización?

La sincronización te permite:

1. **Eliminar álbumes escuchados** de tu colección en GitHub Pages
2. **Añadir nuevos álbumes** desde tu correo
3. **Mantener limpia tu colección** sin acumular música que ya escuchaste

## 📋 Flujo completo

```
┌──────────────────────────────────────────────────────────────┐
│  1. Navegador                                                │
│     • Marcas álbumes como "Escuchado"                       │
│     • Se guardan en localStorage                             │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  2. Exportar localStorage                                    │
│     • Usas sync_tools.html o la consola                     │
│     • Descargas browser_data.json                            │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  3. Script de sincronización                                 │
│     • bc_sync.py lee browser_data.json                      │
│     • Elimina escuchados del JSON                            │
│     • Busca nuevos correos en IMAP                          │
│     • Añade nuevos álbumes                                   │
│     • Guarda bandcamp_data_synced.json                      │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  4. Regenerar sitio                                          │
│     • bc_static_generator.py actualiza HTML                 │
│     • Los escuchados ya no aparecen                          │
│     • Los nuevos sí aparecen                                 │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  5. Subir a GitHub                                           │
│     • git push actualiza tu sitio                            │
│     • Tu localStorage personal NO cambia                     │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Guía paso a paso

### Paso 1: Exportar localStorage del navegador

Tienes **3 métodos** para exportar:

#### Método A: Usando sync_tools.html (MÁS FÁCIL)

1. Abre tu colección de Bandcamp en el navegador
2. Ve a: `https://tu-usuario.github.io/tu-repo/sync_tools.html`
3. Click en **"📥 Exportar localStorage"**
4. Se descarga `browser_data.json`

#### Método B: Bookmarklet

1. Ve a sync_tools.html
2. Arrastra el botón "📥 Exportar Bandcamp" a tu barra de marcadores
3. Desde cualquier página de tu colección, click en el marcador
4. Se descarga automáticamente

#### Método C: Consola del navegador

1. En tu colección, presiona `F12`
2. Ve a "Console"
3. Pega este código:

```javascript
const data = {};
Object.keys(localStorage)
  .filter((key) => key.startsWith("bandcamp_listened_"))
  .forEach((key) => {
    data[key] = JSON.parse(localStorage.getItem(key));
  });

const blob = new Blob([JSON.stringify(data, null, 2)], {
  type: "application/json",
});
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "browser_data.json";
a.click();
```

### Paso 2: Ejecutar script de sincronización

En tu terminal, donde tienes el proyecto:

```bash
# Sincronizar: eliminar escuchados + buscar nuevos
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --interactive \
  --folders "INBOX/Rock:Rock" "INBOX/Jazz:Jazz"
```

**Opciones:**

```bash
# Solo eliminar escuchados (sin buscar nuevos)
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --no-fetch

# No marcar correos como leídos
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --interactive \
  --folders "INBOX/Rock:Rock" \
  --no-mark-read

# Incluir correos ya leídos
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --interactive \
  --folders "INBOX/Rock:Rock" \
  --include-read

# Especificar archivos de entrada/salida
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --input bandcamp_data.json \
  --output bandcamp_data_updated.json \
  --no-fetch
```

### Paso 3: Revisar cambios

El script mostrará:

```
📊 ESTADÍSTICAS DE SINCRONIZACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Álbumes mantenidos: 45
➕ Álbumes nuevos añadidos: 8
➖ Álbumes escuchados eliminados: 12

Total final: 53 álbumes

📁 Por género:

  Rock:
    • Mantenidos: 18
    • Nuevos: 3
    • Eliminados: 5
    • Total: 21

  Jazz:
    • Mantenidos: 27
    • Nuevos: 5
    • Eliminados: 7
    • Total: 32
```

### Paso 4: Regenerar sitio

```bash
python3 bc_static_generator.py --input bandcamp_data_synced.json
```

Si quieres mantener el mismo archivo:

```bash
# Hacer backup primero
cp bandcamp_data.json bandcamp_data_backup.json

# Luego sobrescribir
python3 bc_sync.py ... --output bandcamp_data.json
python3 bc_static_generator.py --input bandcamp_data.json
```

### Paso 5: Revisar localmente (opcional)

```bash
cd docs
python3 -m http.server 8000
```

Visita http://localhost:8000 y verifica que:

- Los álbumes escuchados NO aparecen
- Los nuevos álbumes SÍ aparecen

### Paso 6: Subir a GitHub

```bash
git add docs/ bandcamp_data_synced.json
git commit -m "Sync: removed 12 listened, added 8 new albums"
git push
```

Espera 2-5 minutos y tu sitio estará actualizado.

## 🎯 Casos de uso comunes

### Caso 1: Limpieza mensual

**Situación:** Has escuchado 20 álbumes este mes y quieres limpiar tu colección.

```bash
# 1. Exporta localStorage
# (Usando sync_tools.html)

# 2. Sincroniza y busca nuevos
python3 bc_sync.py --localStorage-file browser_data.json \
  --interactive --folders "INBOX/Rock:Rock"

# 3. Regenera y sube
python3 bc_static_generator.py --input bandcamp_data_synced.json
git add docs/ && git commit -m "Monthly sync" && git push
```

### Caso 2: Solo añadir nuevos (sin eliminar)

**Situación:** Quieres añadir nuevos correos pero mantener todo lo demás.

```bash
# Solo buscar nuevos, sin archivo localStorage
python3 bc_export_to_json.py --interactive \
  --folders "INBOX/Rock:Rock" \
  --output new_albums.json

# Fusionar manualmente o regenerar todo
python3 bc_static_generator.py --input new_albums.json \
  --output-dir docs-new
```

### Caso 3: Solo eliminar escuchados

**Situación:** No tienes nuevos correos, solo quieres limpiar.

```bash
# Exporta localStorage
# ...

# Sincroniza sin buscar nuevos
python3 bc_sync.py --localStorage-file browser_data.json --no-fetch

# Regenera
python3 bc_static_generator.py --input bandcamp_data_synced.json
```

### Caso 4: Resetear todo

**Situación:** Quieres empezar de cero.

```bash
# Opción A: Borrar localStorage en el navegador
# Ve a sync_tools.html → "🗑️ Limpiar escuchados"

# Opción B: Regenerar sin sincronizar
python3 bc_export_to_json.py --interactive \
  --folders "INBOX/Rock:Rock" \
  --include-read
python3 bc_static_generator.py --input bandcamp_data.json
```

## 💡 Tips y mejores prácticas

### 1. Hacer backup antes de sincronizar

```bash
cp bandcamp_data.json backups/bandcamp_data_$(date +%Y%m%d).json
python3 bc_sync.py ...
```

### 2. Revisar en local primero

Siempre prueba localmente antes de hacer push:

```bash
cd docs && python3 -m http.server 8000
```

### 3. Commits descriptivos

```bash
git commit -m "Sync: -5 Rock, -3 Jazz, +8 new albums"
```

### 4. Sincronizar regularmente

Establece una rutina (ej: cada mes) para mantener tu colección limpia.

### 5. Exportar desde el dispositivo principal

Si usas múltiples dispositivos, elige uno como "fuente de verdad" para sincronizar.

## ⚠️ Consideraciones importantes

### localStorage NO se sincroniza automáticamente

Cada dispositivo tiene su propio localStorage. Si marcas álbumes como escuchados en tu laptop, no aparecerán como escuchados en tu móvil.

**Solución:** Exporta desde el dispositivo que más uses.

### El script NO modifica tu localStorage

Cuando sincronizas y regeneras el sitio:

- El JSON se actualiza ✓
- El HTML se regenera ✓
- Tu localStorage local NO cambia ✗

Esto significa que en TU navegador seguirás viendo los álbumes ocultos (porque están en tu localStorage local). Pero para otros usuarios o en otros dispositivos, ya no aparecerán.

**Para verlo en tu navegador:**

1. Limpia localStorage (sync_tools.html → Limpiar)
2. O usa modo incógnito
3. O usa otro navegador

### Los cambios son permanentes

Una vez que eliminas álbumes del JSON y haces push, se eliminan del sitio para todos.

**Solución:** Haz backups del JSON.

## 🔧 Solución de problemas

### "No se encontraron datos de escuchados"

- Verifica que el archivo browser_data.json contenga datos
- Abre el archivo y verifica el formato
- Asegúrate de haber marcado álbumes como escuchados

### "No se pudo conectar al servidor IMAP"

- Verifica credenciales
- Si es Gmail, usa contraseña de aplicación
- Verifica que IMAP esté habilitado

### Los álbumes escuchados siguen apareciendo

- Limpia localStorage en tu navegador
- O verifica en otro dispositivo/navegador
- Asegúrate de que regeneraste el sitio e hiciste push

### El script no elimina los esperado

- Verifica que los IDs coincidan
- Revisa la salida del script (estadísticas)
- Haz un dry-run con --output diferente

## 📊 Formato del archivo browser_data.json

El archivo exportado tiene este formato:

```json
{
  "bandcamp_listened_Rock": ["embed_1234567890", "embed_9876543210"],
  "bandcamp_listened_Jazz": [
    "embed_5555555555",
    "embed_6666666666",
    "embed_7777777777"
  ],
  "bandcamp_listened_Electronic": ["embed_1111111111"]
}
```

Cada clave es `bandcamp_listened_` + nombre del género.
Cada valor es un array de IDs de embeds.

## 🎉 Workflow completo recomendado

```bash
# 1. Una vez al mes (o cuando quieras)
# Exporta localStorage desde sync_tools.html

# 2. Sincroniza
python3 bc_sync.py \
  --localStorage-file browser_data.json \
  --interactive \
  --folders "INBOX/Rock:Rock" "INBOX/Jazz:Jazz"

# 3. Revisa estadísticas
# El script te mostrará qué se eliminó y añadió

# 4. Regenera
python3 bc_static_generator.py --input bandcamp_data_synced.json

# 5. Revisa localmente
cd docs && python3 -m http.server 8000

# 6. Si todo bien, sube
git add .
git commit -m "Monthly sync: cleaned listened, added new"
git push

# 7. (Opcional) Limpia tu localStorage local si quieres
# Ver el sitio "fresco" en tu navegador
```

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
