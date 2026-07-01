# Bandcamp IMAP Collection

Lee correos de Bandcamp desde IMAP, genera una web estática con los embeds de cada álbum organizados por género y la sirve con SSL a través de SWAG.

## Cómo funciona

```
IMAP (correos de Bandcamp)
        ↓
bc_export_to_json.py   →  bc_data.json   (caché en .bandcamp_cache.json)
        ↓
bc_static_generator.py →  docs/*.html
        ↓
server.py (Flask, puerto 8765)
        ↓
SWAG / Nginx  (SSL, subdominio público)
```

La web incluye un botón flotante **"Actualizar colección"** que dispara el pipeline completo sin tocar el terminal. Un timer systemd lo ejecuta también automáticamente cada lunes.

---

## Requisitos previos

- Python ≥ 3.10 con venv en `~/Scripts/python_venv` (incluye Flask)
- Docker con [SWAG](https://docs.linuxserver.io/general/swag) corriendo
- Cuenta de correo con acceso IMAP habilitado
  - Gmail: usar una [App Password](https://myaccount.google.com/apppasswords), no la contraseña normal
- DNS apuntando al servidor para el subdominio que elijas

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tuusuario/bandcamp_imap_mails
cd bandcamp_imap_mails
```

### 2. Crear el archivo de credenciales

```bash
cp .env.example .env
nano .env
```

Valores a rellenar:

```bash
# Credenciales IMAP
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_EMAIL=tu@gmail.com
IMAP_PASSWORD=xxxx_xxxx_xxxx_xxxx   # App Password de Google

# Carpetas IMAP → género (separadas por espacio, con comillas si tienen espacios)
# Formato: "Ruta/IMAP:Nombre del género"
IMAP_FOLDERS="Bandcamp/Rock:Rock Bandcamp/Electronic:Electronic Bandcamp/Jazz:Jazz"

# Álbumes por página en la web
ITEMS_PER_PAGE=10

# Token para el botón de actualización manual (invéntate uno)
UPDATE_TOKEN=mi_token_secreto_aqui

# Puerto local del servidor
PORT=8765
```

> `.env` está en `.gitignore` — nunca se sube al repositorio.

### 3. Primera actualización manual

Comprueba que el pipeline funciona antes de instalar los servicios:

```bash
bash update.sh
```

Debe generar `bc_data.json` y los archivos en `docs/`.

### 4. Instalar los servicios systemd

```bash
sudo cp bandcamp.service        /etc/systemd/system/
sudo cp bandcamp-update.service /etc/systemd/system/
sudo cp bandcamp-update.timer   /etc/systemd/system/

sudo systemctl daemon-reload

# Servidor web (arranca ahora y al reiniciar)
sudo systemctl enable --now bandcamp.service

# Timer semanal (lunes 06:00)
sudo systemctl enable --now bandcamp-update.timer
```

Verifica que está corriendo:

```bash
systemctl status bandcamp.service
curl -s http://127.0.0.1:8765/api/status
```

### 5. Configurar SWAG

Averigua la IP del host desde dentro del contenedor:

```bash
docker inspect swag | grep -i gateway
# Normalmente: 172.17.0.1
```

Edita `bandcamp.subdomain.conf` si la IP es diferente, luego cópialo al volumen de SWAG:

```bash
sudo cp bandcamp.subdomain.conf \
    /path/to/swag/config/nginx/proxy-confs/bandcamp.subdomain.conf

docker restart swag
```

La web quedará en `https://bandcamp.tudominio.com`.

---

## Uso diario

### Actualización manual desde la web

Usa el botón **"Actualizar colección"** en la esquina inferior derecha de cualquier página. Muestra el estado en tiempo real y recarga automáticamente al terminar.

### Actualización manual desde el terminal

```bash
bash update.sh
```

### Ver logs

```bash
# Logs del servidor web en vivo
journalctl -u bandcamp.service -f

# Logs de la última actualización automática
journalctl -u bandcamp-update.service --no-pager
```

### Administrar el timer

```bash
# Ver cuándo se ejecutará la próxima vez
systemctl list-timers bandcamp-update.timer

# Forzar la actualización ahora (sin esperar al lunes)
sudo systemctl start bandcamp-update.service
```

---

## Estructura del proyecto

```
bandcamp_imap_mails/
├── server.py                  # Servidor Flask (sirve docs/ + API de actualización)
├── update.sh                  # Pipeline: IMAP → JSON → HTML
├── bc_export_to_json.py       # Descarga correos IMAP y exporta a JSON
├── bc_static_generator.py     # Genera HTML estático desde el JSON
├── bc_cache_system.py         # Caché de correos ya procesados
├── bc_imap_generator.py       # Utilidades IMAP y extracción de embeds
├── docs/                      # HTML generado (servido por Flask y SWAG)
│   ├── index.html
│   ├── *.html                 # Una página por género
│   └── images/
├── .bandcamp_cache.json       # Caché local (gitignored)
├── bc_data.json               # JSON intermedio (gitignored)
├── .env                       # Credenciales (gitignored)
├── .env.example               # Plantilla de credenciales
├── bandcamp.service           # Systemd: servidor web
├── bandcamp-update.service    # Systemd: servicio de actualización
├── bandcamp-update.timer      # Systemd: timer semanal (lunes 06:00)
└── bandcamp.subdomain.conf    # Nginx config para SWAG
```

---

## Solución de problemas

**El servidor no arranca**
```bash
journalctl -u bandcamp.service -n 50
# Comprueba que .env existe y que la ruta del venv es correcta en bandcamp.service
```

**Error de conexión IMAP**
```bash
bash update.sh
# Lee el mensaje — suele ser contraseña incorrecta o App Password no generada
```

**SWAG devuelve 502 Bad Gateway**
```bash
# El servidor local no está corriendo o la IP del host es incorrecta
systemctl status bandcamp.service
docker inspect swag | grep -i gateway
# Actualiza $upstream_app en bandcamp.subdomain.conf y reinicia SWAG
```

**El botón de actualización devuelve 403**
```bash
# UPDATE_TOKEN en .env no coincide con el que cargó el servidor
sudo systemctl restart bandcamp.service
```
