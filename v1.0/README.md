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
