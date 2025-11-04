# 🎵 Bandcamp Collection para GitHub Pages

Convierte tus correos de Bandcamp en una colección web estática y hermosa que puedes hostear gratis en GitHub Pages. Marca álbumes como "escuchados" y sincroniza tu colección automáticamente.

![Theme](https://img.shields.io/badge/theme-dark-14141e)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)

## ✨ Características

- 🎨 **Diseño oscuro moderno** con gradientes personalizados
- 💾 **Persistencia local** usando localStorage
- 🔄 **Sincronización inteligente** - Elimina escuchados, añade nuevos
- 🎵 **Auto-stop** - Un solo reproductor sonando a la vez
- 📱 **Responsive** - Funciona en todos los dispositivos
- 🆓 **100% gratis** - Hostea en GitHub Pages
- 🔒 **Privado** - Tus datos nunca salen del navegador

## 🚀 Inicio Rápido

### 1. Genera una demo

```bash
python3 generate_demo.py
# Abre demo-site/index.html en tu navegador
```

### 2. Usa tus datos reales

```bash
# Exporta correos
python3 bc_export_to_json.py --interactive \
  --folders "INBOX/Rock:Rock" "INBOX/Jazz:Jazz"

# Genera el sitio
python3 bc_static_generator.py --input bandcamp_data.json

# Preview local
cd docs && python3 -m http.server 8000
```

### 3. Publica en GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/tu-usuario/tu-repo.git
git push -u origin main
```

Luego en GitHub: **Settings → Pages → Source: main → Folder: /docs**

Tu sitio estará en: `https://tu-usuario.github.io/tu-repo/`

## 🔄 Sincronización

### ¿Qué hace?

- ➖ Elimina álbumes que ya escuchaste
- ➕ Añade nuevos del correo
- 🎯 Mantiene tu colección limpia

### Cómo sincronizar

1. **Exporta localStorage** desde tu colección web:
   - Ve a `tu-sitio.github.io/sync_tools.html`
   - Click en **"📥 Exportar localStorage"**
   - Descargas `browser_data.json`

2. **Ejecuta sincronización**:

```bash
python3 bc_sync.py --localStorage-file browser_data.json \
  --interactive --folders "INBOX/Rock:Rock"
```

3. **Regenera y publica**:

```bash
python3 bc_static_generator.py --input bandcamp_data_synced.json
git add docs/ && git commit -m "Sync" && git push
```

## 📦 Scripts Incluidos

- `bc_export_to_json.py` - Exporta correos IMAP a JSON
- `bc_static_generator.py` - Genera sitio HTML estático
- `bc_sync.py` - Sincroniza localStorage con nuevos correos
- `generate_demo.py` - Demo rápida
- `setup.sh` - Menú interactivo de instalación

## 🎨 Personalización

### Cambiar colores

Edita `bc_static_generator.py`:

```python
background: linear-gradient(135deg, #14141e 0%, #2d1b4e 100%);
```

### Álbumes por página

```bash
python3 bc_static_generator.py --input bandcamp_data.json --items-per-page 20
```

## 📋 Requisitos

- Python 3.7+
- Git
- Cuenta de GitHub
- Cuenta de correo con IMAP (Gmail, Outlook, etc.)

## 💡 Tips

### Gmail

Usa **Contraseña de aplicación**:

1. Google → Seguridad
2. Verificación en 2 pasos (actívala)
3. Contraseñas de aplicaciones
4. Genera una para "Correo"

### Organización

Crea carpetas en tu correo:

- `INBOX/Rock`
- `INBOX/Electronic`
- `INBOX/Jazz`

```bash
python3 bc_export_to_json.py --interactive \
  --folders "INBOX/Rock:Rock" "INBOX/Electronic:Electronic"
```

## 🎯 Casos de Uso

- **To-Listen List** - Tu colección es tu lista de pendientes
- **Curación Musical** - Solo muestras álbumes que recomiendas
- **Limpieza Regular** - Cada mes eliminas escuchados y añades nuevos
- **Descubrimiento** - Trackeas qué te falta escuchar

## 🔧 Características Técnicas

- **Frontend**: HTML + CSS + JavaScript vanilla
- **Persistencia**: localStorage (cliente)
- **Embeds**: iFrames de Bandcamp
- **Auto-stop**: Detiene reproductores automáticamente
- **Hosting**: GitHub Pages (gratis)
- **Backend**: Ninguno (todo estático)

## 📖 Documentación

Incluye documentación detallada:

- `START_HERE.md` - Empieza aquí
- `SYNC_GUIDE.md` - Guía de sincronización completa
- `ARCHITECTURE.md` - Cómo funciona todo
- `LOCALSTORAGE_EXPLAINED.md` - Detalles técnicos

## 🐛 Troubleshooting

**Error de autenticación IMAP**

- Gmail: usa contraseña de aplicación
- Verifica que IMAP esté activado

**Los escuchados siguen apareciendo**

- Es normal en TU navegador (tienes localStorage)
- Verifica en otro dispositivo o modo incógnito

**No se detienen los reproductores**

- Actualiza la página
- Asegúrate de hacer click en el área del embed

## 🤝 Contribuir

¿Ideas para mejorar? ¡Abre un issue o pull request!

## 📄 Licencia

MIT License - Uso libre para proyectos personales

## 🎉 Créditos

- Embeds cortesía de [Bandcamp](https://bandcamp.com)
- Inspirado en coleccionistas de música de todo el mundo
