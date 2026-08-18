# Portafolio de Iniciativas de ANC — v1.0

Backend FastAPI + SQL Server. Ver los `README.md` dentro de cada módulo
(`usuarios/`, `ideas/`, `revision/`, etc.) para el propósito de cada uno.

## Entorno de desarrollo local con Docker (sin depender de IT)

Esto levanta una instancia de SQL Server local en Docker para poder
desarrollar y probar mientras se gestiona la instancia real con IT.
**Solo para desarrollo local — nunca usar esta configuración en producción.**

### 1. Preparar variables de entorno

```bash
cp .env.docker.example .env.docker   # y ajustar SA_PASSWORD
cp .env.example .env                 # y poner DB_PASSWORD = el mismo valor que SA_PASSWORD
```

`.env` y `.env.docker` están gitignorados — nunca se commitean.

### 2. Levantar el contenedor

```bash
docker compose --env-file .env.docker up -d
```

Espera a que el healthcheck del contenedor esté en estado `healthy`
(la primera vez SQL Server tarda unos segundos en inicializar):

```bash
docker compose ps
```

### 3. Crear la base de datos

El contenedor arranca sin la base `portafolio_iniciativas_anc` creada —
solo trae `master`. Crearla una vez, contra el propio contenedor:

```bash
docker exec -it portafolio-iniciativas-sqlserver \
  /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "<SA_PASSWORD>" \
  -Q "CREATE DATABASE portafolio_iniciativas_anc"
```

### 4. Instalar dependencias y correr la migración

Requiere tener instalado el [ODBC Driver 17 (o 18) para SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
en la máquina donde corre la app (no dentro del contenedor).

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 5. Verificar la conexión

```bash
uvicorn main:app --reload --port 8010
```

Luego, en otra terminal:

```bash
curl http://localhost:8010/health
curl http://localhost:8010/usuarios
```

`/usuarios` debe responder `[]` en una base recién migrada, sin usuarios
creados todavía.

### Apagar / limpiar

```bash
docker compose down          # detiene el contenedor, conserva los datos
docker compose down -v       # detiene y borra también el volumen de datos
```

## Autenticación — estado real

El proyecto tiene **dos caminos de identidad activos en paralelo**, y la
diferencia importa para cualquiera que despliegue o audite esto:

### 1. Login con Microsoft Entra ID (MSAL) — implementado y activo

Ya no es andamiaje pendiente: hoy funciona de punta a punta contra el
tenant real de Grupo ANC.

- **Frontend**: `frontend/.env` ya tiene credenciales reales cargadas
  (`VITE_AZURE_CLIENT_ID`, `VITE_AZURE_TENANT_ID`). Con ambas presentes,
  `azureAdConfigurado` (`frontend/src/core/authConfig.ts`) es `true`, el
  botón "Iniciar sesión con Microsoft" aparece en el header
  (`LoginScreen.tsx`), y cada request al backend manda
  `Authorization: Bearer <token>` obtenido vía `acquireTokenSilent`
  (`frontend/src/core/api.ts`), en vez de la cabecera simulada.
- **Backend**: `core/auth.py` valida el token de verdad — **no** es un
  stub. Descarga y cachea las claves públicas (JWKS) del tenant, verifica
  la firma RS256, el `audience` (`settings.azure_api_audience`) y el
  `issuer` contra el tenant configurado (`settings.azure_tenant_id`), y
  `jose` valida la expiración. La función `validar_token_azure` tiene
  implementación completa; no lanza `NotImplementedError`.
- Estos valores (`azure_tenant_id`, `azure_api_audience`) son constantes
  de la app registrada en Azure AD, con default ya cargado en
  `core/config.py` — no dependen de credenciales por-ambiente adicionales
  para que la validación funcione.

### 2. Fallback `X-Usuario-Id` — decisión consciente, no un bug

`usuarios/dependencies.py:obtener_identidad_autenticada` acepta un segundo
camino: si la request no trae `Authorization: Bearer`, confía en el header
`X-Usuario-Id` tal cual, sin firma ni verificación — solo hace
`db.get(Usuario, x_usuario_id)`.

**Esto está activo a propósito**, para que compañeros de prueba puedan
entrar sin depender de que IT complete el alta de su cuenta en Azure AD o
de que tengan acceso al tenant todavía. El equipo decidió mantenerlo así
**hasta nueva orden** — no es una brecha accidental, es un trade-off
tomado conscientemente entre fricción de testing y superficie de ataque.

Puntos a tener presentes mientras esta decisión siga en pie:
- **No está gateado por `ENTORNO`** (a diferencia de `/auth/dev-login`,
  ver abajo) — la rama `X-Usuario-Id` de `obtener_identidad_autenticada`
  es alcanzable sin importar el valor de `settings.entorno`. Quien tenga
  la URL del backend puede autenticarse como cualquier `usuario_id` que
  exista en la base, sin credenciales reales, mientras este camino siga
  abierto.
- Todos los checks de rol (`requerir_admin`, `_validar_acceso_comite`,
  `_puede_ver_idea`, etc.) confían en la identidad que devuelva esta
  función — si `X-Usuario-Id` queda abierto, esos checks siguen
  funcionando correctamente pero sobre una identidad no verificada.
- Cuando se decida cerrar este camino en producción, el cambio es
  puntual: condicionar esa rama de `obtener_identidad_autenticada` a
  `settings.entorno == "development"` (mismo patrón que ya usa
  `/auth/dev-login`), no un rediseño.

### `/auth/dev-login` — sí está gateado por entorno

Aparte de `X-Usuario-Id`, existe `POST /auth/dev-login`
(`core/dev_router.py`) — accesos rápidos por correo para previsualizar
cada rol sin pasar por Azure AD. Este router **solo se registra si
`settings.entorno == "development"`** (ver `main.py`), con default
`"production"` en `core/config.py:24` — un `.env` faltante o mal copiado
nunca lo activa por error. Es un mecanismo más acotado y sí apagado en
producción, distinto de `X-Usuario-Id`.

## Configuración de IA (Claude)

`CLAUDE_STUB_MODE` (`core/config.py:15`) tiene default `true`: mientras no
se setee explícitamente `CLAUDE_STUB_MODE=false` junto con un
`CLAUDE_API_KEY` real, toda la integración con Claude (entrevista, resumen
de idea, clasificación, asignación de revisor, generación de documentos)
devuelve respuestas simuladas con el prefijo `[STUB]`. Confirmar el valor
de estas dos variables antes de considerar un ambiente "en producción con
IA real".

## Problemas conocidos

### ✅ Resuelto — 2 gaps de autorización (escritura en ideas ajenas, lectura de perfiles ajenos)

Corregidos en esta sesión: `POST /ideas/{id}/mensajes` y `POST
/ideas/{id}/enviar` ahora exigen que quien llama sea el autor de la idea o
un admin (antes cualquier usuario autenticado podía escribir/enviar una
idea ajena solo conociendo el `idea_id`); y `GET /usuarios/{usuario_id}`
ahora exige que sea el propio usuario o un admin (antes cualquier usuario
autenticado podía leer el perfil completo de cualquier otro).

### ✅ Resuelto — encoding varchar/CP1252 en columnas de texto libre

Este problema estuvo documentado acá como crítico y ya se corrigió:
- Migración aplicada: `alembic/versions/1a2b3c4d5e6f_fix_encoding_varchar_a_nvarchar.py`
  (encadenada en la historia real de Alembic, entre `8601a283f177` y
  `2b7e5f9a1c3d`) — convierte a `NVARCHAR`/`NVARCHAR(MAX)` las columnas de
  texto libre generadas por IA o por usuarios (mensajes de entrevista,
  retroalimentación, justificaciones, nombres, rutas de archivo, etc.),
  dejando aparte las columnas de tipo enum/código corto en ASCII puro.
- `core/database.py` ya configura `setencoding()` explícito (UTF-16LE /
  `SQL_WCHAR`) además del `setdecoding()` que ya tenía, cerrando la causa
  raíz (pyodbc ya no reutiliza CP1252 para escribir parámetros).

Si en algún ambiente todavía se ve `UnicodeEncodeError` o texto corrupto
con tildes/ñ/emojis/comillas tipográficas, confirmar primero que esa base
tiene aplicada la migración `1a2b3c4d5e6f` (`alembic current`) antes de
asumir que es este mismo problema otra vez.

### Puerto 8000 con reserva fantasma (Windows, este equipo)

El puerto por defecto de desarrollo de este backend es **8010, no el
8000** convencional de FastAPI/uvicorn. En el equipo Windows donde se
desarrolló este módulo, el puerto 8000 quedó con una reserva TCP
fantasma: `netstat -ano | findstr :8000` muestra PIDs en estado
`LISTENING`, pero esos PIDs no corresponden a ningún proceso real
(`Get-Process`/`taskkill /F` confirman que no existen), y el puerto
tampoco está dentro de los rangos administrados por Hyper-V/WSL2
(`netsh interface ipv4 show excludedportrange`). Es un socket huérfano
que Windows no libera aunque se maten los PIDs reportados.

La solución conocida para este tipo de reserva fantasma es reiniciar el
servicio de red (`net stop winnat && net start winnat`) o `wsl
--shutdown`. Ambas opciones reinician toda la red virtual de
Hyper-V/WSL2, lo que **tumbaría el contenedor Docker de SQL Server**
(`portafolio-iniciativas-sqlserver`) y cualquier otro contenedor en
ejecución. Por eso, mientras no sea estrictamente necesario liberar el
8000, se evita tocar esa configuración y en su lugar el proyecto usa
**8010** como puerto estándar de desarrollo (`PORT` en `.env.example`,
`VITE_API_URL` en `frontend/.env.example`).

Si en otro equipo el 8000 funciona sin problema, no hay nada que
cambiar — el valor de `PORT`/`VITE_API_URL` en `.env` es local a cada
entorno.

### Recuperación de PIN de admin — todavía manual

El módulo `criterios/` (documentos de IA versionados) usa un PIN personal
por admin para autorizar subidas/ediciones de documentos. Hoy, si un
admin olvida su PIN, no hay flujo de autoservicio — la única opción es
que un desarrollador lo restablezca manualmente con
`v1.0/scripts/resetear_pin_emergencia.py` directamente contra la base de
datos.

Con el login de Microsoft ya activo (ver arriba) y el correo institucional
ya disponible por usuario, esto es ahora técnicamente viable de resolver
con un flujo de recuperación por correo (enlace de un solo uso, similar a
"olvidé mi contraseña") — sigue pendiente de implementar, ya no de
credenciales de IT.

### Otras piezas pendientes de decisión de negocio, no de código

Estas quedaron identificadas en revisiones recientes y no son bugs, sino
alcance por definir:
- `clasificacion/models.py` — una regla de negocio de clasificación
  todavía depende de una definición pendiente del área de negocio.
- `notificaciones/` — el envío de correo de escalamiento está en stub
  (sin credenciales SMTP configuradas); el escalamiento in-app funciona.
- CAB y criterios de IA de entrevista son hoy entidades globales, no
  scoped por departamento — ver `diseno-pendiente/` si se aprueba avanzar
  con ese cambio.
