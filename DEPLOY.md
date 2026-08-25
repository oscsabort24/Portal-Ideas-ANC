# Runbook de despliegue — Portal de Ideas ANC

Procedimiento operativo para desplegar cambios en producción y recuperarse si
algo sale mal. Escrito para seguirse de punta a punta sin contexto previo.

---

## 1. Datos del entorno

| Qué | Valor |
|---|---|
| Servidor | `anccrwe03` |
| Ruta del repo en el servidor | `/opt/portal-ideas-anc` |
| Dominio público | `https://ideas.ancwebapps.com` |
| Archivo de compose | `docker-compose.prod.yml` |
| Backups | `/opt/portal-ideas-anc/backups/` |

### Contenedores y puertos

| Servicio | Contenedor | Puerto en el host | Imagen |
|---|---|---|---|
| `backend` | `portal-ideas-backend` | `8010` → 8010 | se construye (`Dockerfile.backend`) |
| `frontend` | `portal-ideas-frontend` | `8020` → 80 | se construye (`Dockerfile.frontend`) |
| `sqlserver` | `portal-ideas-sqlserver` | `127.0.0.1:1450` → 1433 | imagen oficial, no se construye |

El puerto de SQL Server está bindeado **solo a localhost** a propósito. Para
conectarte con un cliente SQL desde tu máquina, usá un túnel SSH:

```bash
ssh -L 1450:localhost:1450 usuario@anccrwe03
# y apuntá el cliente a localhost:1450
```

El destino del túnel tiene que ser `localhost`, no la IP de red del servidor.

### Base de datos

- Nombre: `portafolio_iniciativas_anc`
- Edición: **SQL Server Express** (licenciada para producción; Developer no lo está)
- Límite de Express: 10 GB por base. Hoy pesa ~16 MB.
- Volumen de datos: `portal_ideas_sqlserver_data` (volumen nombrado de Docker)

---

## 2. ⚠️ Los archivos `.env` viven SOLO en el servidor

**`.env` y `.env.backend` NO están en git y nunca deben comitearse.** Están en
`.gitignore` y existen únicamente en `/opt/portal-ideas-anc/` del servidor.
Contienen credenciales reales (contraseña de `sa`, API key de Claude).

Si se pierden, **no se recuperan del repo**. Guardá una copia en el gestor de
contraseñas del equipo.

### `/opt/portal-ideas-anc/.env`

Lo lee **Docker Compose** para resolver los `${...}` de `docker-compose.prod.yml`:

```
SA_PASSWORD=...
VITE_API_URL=https://ideas.ancwebapps.com/api
VITE_AZURE_CLIENT_ID=...
VITE_AZURE_TENANT_ID=...
```

### `/opt/portal-ideas-anc/.env.backend`

Se inyecta **dentro del contenedor backend** (`env_file:` en el compose):

```
ENTORNO=production          # NUNCA "development" acá (ver abajo)
CORS_ALLOWED_ORIGINS=https://ideas.ancwebapps.com
DB_SERVER=sqlserver         # nombre del servicio, red interna de compose
DB_PORT=1433
DB_NAME=portafolio_iniciativas_anc
DB_USER=sa
DB_PASSWORD=...
CLAUDE_API_KEY=...
```

Dos valores con consecuencias de seguridad directas:

- **`ENTORNO=production`** apaga dos bypasses de autenticación: el endpoint
  `/auth/dev-login` y el header `X-Usuario-Id`. Con `development`, cualquiera
  puede actuar como cualquier usuario —incluido un admin— sin credenciales.
- **`CORS_ALLOWED_ORIGINS`** no puede contener `*`. La app usa
  `allow_credentials=True`, y esa combinación deja que cualquier sitio haga
  requests autenticadas contra la API. Si ponés `*`, **el backend se niega a
  arrancar** a propósito (validación en `v1.0/core/config.py`).

---

## 3. Hacer un cambio (en tu máquina)

```bash
# 1. Diagnóstico: entender qué se rompe y por qué, antes de tocar nada.

# 2. Aplicar el cambio y revisar el diff ANTES de commitear.
git diff

# 3. Commitear. Un commit por hallazgo/tema, no todo junto:
#    hace revisable el historial y permite revertir uno sin arrastrar el resto.
git add <archivos-especificos>     # nunca "git add ." a ciegas
git status                          # confirmar qué quedó staged
git commit

# 4. Confirmar qué se va a subir, y recién ahí pushear.
git log origin/main..HEAD --oneline
git push
```

**Nunca commitear:** `.claude/settings.local.json`, `prototipo-v0.1/server.js`
(cambios locales de trabajo), ni ningún `.env*`.

---

## 4. Aplicar el cambio en el servidor

```bash
ssh usuario@anccrwe03
cd /opt/portal-ideas-anc
git pull
```

Después, **según qué cambió**:

### 4.1 Tabla de decisión

| Cambió | Comando | ¿Rebuild? |
|---|---|---|
| Código Python (`v1.0/**`) | `docker compose -f docker-compose.prod.yml up -d --build backend` | Sí |
| `v1.0/requirements.txt` | `docker compose -f docker-compose.prod.yml up -d --build backend` | Sí (lento, ver 4.2) |
| Código del frontend (`frontend/**`) | `docker compose -f docker-compose.prod.yml up -d --build frontend` | Sí |
| `VITE_*` en `.env` | `docker compose -f docker-compose.prod.yml up -d --build frontend` | **Sí** (ver 4.3) |
| `.env.backend` (cualquier variable) | `docker compose -f docker-compose.prod.yml up -d backend` | No, solo recrear |
| Config de `sqlserver` en el compose | `docker compose -f docker-compose.prod.yml up -d sqlserver` | No, solo recrear |
| Solo `DEPLOY.md`, `scripts/`, docs | nada | No |

`up -d` **sin** `--build` recrea el contenedor con la imagen existente: sirve
para cambios de configuración, **no** para cambios de código. Si cambiaste
código y no ponés `--build`, el deploy parece exitoso pero sigue corriendo la
versión vieja.

### 4.2 Rebuild del backend: cuánto tarda

`Dockerfile.backend` copia `requirements.txt` **antes** del `pip install`, así
que:

- **Solo cambió código Python** → se invalida únicamente la capa final
  (`COPY v1.0/ .`). Rebuild rápido, ~10-20 s.
- **Cambió `requirements.txt`** → se invalida el `pip install` **y** el
  `playwright install --with-deps chromium`. Rebuild lento, varios minutos.
  Es esperado, no es un problema.

Las **migraciones de Alembic corren solas** al arrancar el backend: el `CMD`
del Dockerfile es `alembic upgrade head && uvicorn main:app ...`. No hay que
correrlas a mano. Si una migración falla, el contenedor no levanta — revisá
los logs (sección 5).

### 4.3 Por qué cambiar `VITE_API_URL` exige `--build`

Las variables `VITE_*` se **hornean en el bundle de JavaScript durante el
build** (son `ARG`/`ENV` antes del `npm run build`). No se leen en tiempo de
ejecución. Reiniciar el contenedor no cambia nada: hay que reconstruir la
imagen para que el nuevo valor entre al bundle.

Corolario: esos valores son **públicos**, quedan visibles en el JS servido al
navegador. El client id y el tenant id de Azure AD son públicos por diseño, así
que está bien — pero **nunca** pongas un secreto real en un `VITE_*`.

### 4.4 Deploy completo (cuando no estás seguro)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Reconstruye lo que haga falta y recrea lo que cambió. Más lento, pero seguro.

---

## 5. Verificación post-deploy

Correr **siempre**, en este orden:

```bash
# 1. Los tres contenedores arriba y sanos
docker compose -f docker-compose.prod.yml ps

# 2. El backend responde
curl -s https://ideas.ancwebapps.com/api/health
# esperado: {"status":"ok"}

# 3. Sin errores en el arranque
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

En los logs del backend, al arrancar bien vas a ver:

```
WARNING: Config efectiva de este proceso: CLAUDE_STUB_MODE=... | CLAUDE_API_KEY=presente | ...
INFO:    Application startup complete.
```

Si aparece `ENTORNO=development: /auth/dev-login está activo`, **pará todo**:
`.env.backend` quedó mal y la app está con los bypasses de autenticación
abiertos.

### 5.1 Confirmar bindings de puertos

Cuando el cambio toca puertos del compose:

```bash
ss -ltnp | grep -E '1450|8010|8020'
```

Esperado:

```
LISTEN 0 4096 127.0.0.1:1450 ...   ← SQL Server: SOLO localhost
LISTEN 0 4096   0.0.0.0:8010 ...   ← backend
LISTEN 0 4096   0.0.0.0:8020 ...   ← frontend
```

Si `1450` aparece como `0.0.0.0:1450` o `*:1450`, el contenedor no tomó la
config nueva. Forzalo:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate sqlserver
```

### 5.2 Prueba de humo de autenticación

```bash
# Sin credenciales → debe dar 401
curl -s https://ideas.ancwebapps.com/api/ideas

# Con X-Usuario-Id → debe dar 401 también (bypass cerrado en producción)
curl -s -H "X-Usuario-Id: 1" https://ideas.ancwebapps.com/api/ideas
```

Ambas deben responder `{"detail":"Falta autenticación: Authorization Bearer"}`.
Si la segunda devuelve `200`, `ENTORNO` no está en `production`.

---

## 6. Backups

### 6.1 El script

`scripts/backup_db.sh` hace `BACKUP DATABASE`, verifica la integridad del
archivo con `RESTORE VERIFYONLY`, lo copia al host y purga los de más de 14
días. Loguea todo a `/opt/portal-ideas-anc/backups/backup.log`.

Correrlo a mano en cualquier momento es seguro: `BACKUP DATABASE` no bloquea la
base ni interrumpe a los usuarios.

```bash
cd /opt/portal-ideas-anc
./scripts/backup_db.sh
```

### 6.2 Programarlo por cron (diario a las 2am)

Una sola vez, en el servidor:

```bash
chmod +x /opt/portal-ideas-anc/scripts/backup_db.sh
sudo crontab -e
```

Agregar esta línea:

```cron
0 2 * * * /opt/portal-ideas-anc/scripts/backup_db.sh >> /opt/portal-ideas-anc/backups/cron.log 2>&1
```

Va en el crontab de **root** (o de un usuario del grupo `docker`), porque el
script usa `docker exec`. Verificar que quedó:

```bash
sudo crontab -l
```

Y probar que corre bien **antes** de confiar en él:

```bash
sudo /opt/portal-ideas-anc/scripts/backup_db.sh
ls -la /opt/portal-ideas-anc/backups/
```

Si falla solo bajo cron pero funciona a mano, casi siempre es el `PATH`: cron
usa uno mínimo. Se arregla poniendo `PATH=/usr/local/bin:/usr/bin:/bin` como
primera línea del crontab.

### 6.3 Chequeo periódico

Que el cron esté puesto no garantiza que esté funcionando. Una vez por semana:

```bash
ls -la /opt/portal-ideas-anc/backups/          # ¿hay un .bak de hoy?
tail -20 /opt/portal-ideas-anc/backups/backup.log
```

---

## 7. Restaurar un backup

**Solo ante pérdida o corrupción de datos.** Sobrescribe la base completa: todo
lo posterior al backup se pierde.

```bash
cd /opt/portal-ideas-anc

# 1. Elegir el backup
ls -la backups/

# 2. Bajar el backend para que suelte sus conexiones.
#    RESTORE necesita acceso exclusivo a la base.
docker compose -f docker-compose.prod.yml stop backend

# 3. Copiar el .bak dentro del contenedor de SQL Server
docker cp backups/backup_2026-08-25_0200.bak portal-ideas-sqlserver:/tmp/restore.bak

# 4. Restaurar
docker exec -it portal-ideas-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -C -S localhost -U sa -P "$SA_PASSWORD" -b -Q \
  "ALTER DATABASE [portafolio_iniciativas_anc] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
   RESTORE DATABASE [portafolio_iniciativas_anc] FROM DISK = N'/tmp/restore.bak' WITH REPLACE;
   ALTER DATABASE [portafolio_iniciativas_anc] SET MULTI_USER;"

# 5. Limpiar y levantar el backend.
#    El -u root es necesario: "docker cp" dejó el archivo como root, y
#    "docker exec" sin -u corre como el usuario mssql, que no puede
#    borrarlo (/tmp es sticky). Sin el -u root falla con
#    "Operation not permitted".
docker exec -u root portal-ideas-sqlserver rm -f /tmp/restore.bak
docker compose -f docker-compose.prod.yml start backend

# 6. Verificar
curl -s https://ideas.ancwebapps.com/api/health
docker compose -f docker-compose.prod.yml logs --tail=30 backend
```

`SET SINGLE_USER WITH ROLLBACK IMMEDIATE` corta cualquier conexión que haya
quedado viva. Sin eso, `RESTORE` falla con "database is in use".

Al levantar, el backend corre `alembic upgrade head` automáticamente. Si el
backup es de una versión de esquema anterior, las migraciones que falten se
aplican solas.

---

## 8. Si algo sale mal

### El contenedor no levanta

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

Sospechosos habituales, en orden:

1. **Migración de Alembic fallida** → el `CMD` corta antes de uvicorn. El
   traceback está en los logs.
2. **`CORS_ALLOWED_ORIGINS` con `*`** → el backend aborta a propósito con un
   `ValidationError` que lo dice explícito. Arreglá `.env.backend`.
3. **SQL Server todavía arrancando** → `depends_on: condition: service_healthy`
   debería evitarlo, pero si el healthcheck expira, reintentá el `up -d`.
4. **Falta una variable en `.env.backend`** → error de pydantic nombrando el campo.

### Volver a la versión anterior

```bash
git log --oneline -10
git checkout <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
```

Para volver a la última versión: `git checkout main`.

### Recrear un servicio desde cero

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate <servicio>
```

⚠️ **Nunca** uses `docker compose down -v` en producción: el `-v` borra el
volumen `portal_ideas_sqlserver_data`, o sea **toda la base de datos**. Sin `-v`
es seguro (los volúmenes sobreviven).

### Recrear sqlserver no requiere reiniciar el backend

`v1.0/core/database.py` crea el engine con `pool_pre_ping=True`: SQLAlchemy
detecta las conexiones muertas y reconecta solo. El primer request después de
la recreación paga el reconnect; el resto sale normal. Verificado en la
práctica.

Ojo con la confusión frecuente: `depends_on: condition: service_healthy`
controla **solo el orden de arranque**, no reinicia el backend cuando sqlserver
se recrea. Lo que salva ahí es `pool_pre_ping`, no `depends_on`.

---

## 9. Comandos de referencia rápida

```bash
# Estado
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend

# Deploy típico tras un cambio de código Python
git pull && docker compose -f docker-compose.prod.yml up -d --build backend

# Deploy típico tras un cambio de código del frontend
git pull && docker compose -f docker-compose.prod.yml up -d --build frontend

# Aplicar un cambio de .env.backend (sin rebuild)
docker compose -f docker-compose.prod.yml up -d backend

# Backup manual
./scripts/backup_db.sh

# Consola SQL
docker exec -it portal-ideas-sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -C -S localhost -U sa -P "$SA_PASSWORD" -d portafolio_iniciativas_anc

# Health
curl -s https://ideas.ancwebapps.com/api/health
```
