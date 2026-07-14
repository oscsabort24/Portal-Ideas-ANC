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
uvicorn main:app --reload
```

Luego, en otra terminal:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/usuarios
```

`/usuarios` debe responder `[]` en una base recién migrada, sin usuarios
creados todavía.

### Apagar / limpiar

```bash
docker compose down          # detiene el contenedor, conserva los datos
docker compose down -v       # detiene y borra también el volumen de datos
```

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
