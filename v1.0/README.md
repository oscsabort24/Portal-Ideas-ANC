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

## Problemas conocidos

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

## Login con Microsoft Entra ID (MSAL) — pendiente de IT

El andamiaje de login con Microsoft ya está en el código (frontend con
MSAL, backend con `core/auth.py`), pero **no está activo** porque faltan
credenciales reales. Mientras no lleguen, la app sigue funcionando con
el usuario simulado de siempre (`frontend/src/core/UsuarioActualContext.tsx`)
y la verificación de rol admin sigue siendo la temporal por header
`X-Usuario-Id` (`usuarios/dependencies.py`).

### Qué falta pedirle a IT (Arnoldo)

Registrar una app en Microsoft Entra ID (Azure AD) para este proyecto y
compartir:

1. **Tenant ID** — identificador del directorio de Grupo ANC en Azure AD.
2. **Client ID** (Application ID) — de la app registrada para este portal.
3. **Client Secret** — solo necesario si en el futuro el backend valida
   tokens directamente contra Azure AD (hoy `core/auth.py` está sin
   implementar, así que esto puede pedirse después).
4. Confirmar el **redirect URI** permitido (hoy pensado como la URL raíz
   del frontend, ej. `http://localhost:5173/` en desarrollo).

### Dónde van esas credenciales una vez que lleguen

- Frontend (`frontend/.env`, nunca comitear):
  ```
  VITE_AZURE_CLIENT_ID=<Client ID>
  VITE_AZURE_TENANT_ID=<Tenant ID>
  ```
  En cuanto estas dos variables tengan valor, el botón "Iniciar sesión
  con Microsoft" aparece automáticamente en el header y el login real
  con MSAL queda activo (`frontend/src/core/authConfig.ts` y
  `AuthProvider.tsx`).
- Backend: implementar `validar_token_azure` en `core/auth.py` (hoy
  lanza `NotImplementedError` a propósito) y conectar `Client Secret`
  cuando se decida validar tokens en el servidor en vez de confiar en
  el frontend.

### Otro pendiente relacionado: recuperación de PIN por correo

**Recuperación de PIN por correo — bloqueado hasta tener login real con
correo institucional vinculado.** El módulo `criterios/` (documentos de
IA versionados) usa un PIN personal por admin para autorizar subidas de
documentos. Hoy, si un admin olvida su PIN, no hay forma de recuperarlo
vía la app — la única opción es que un desarrollador lo restablezca
manualmente con `v1.0/scripts/resetear_pin_emergencia.py` directamente
contra la base de datos. Una vez que el login de Microsoft Entra ID esté
conectado y cada usuario tenga su correo institucional verificado, se
puede reemplazar esto por un flujo de recuperación por correo (enlace
de un solo uso, similar a "olvidé mi contraseña").
