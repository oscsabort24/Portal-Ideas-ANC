#!/usr/bin/env bash
#
# Backup diario de la base de datos del Portal de Ideas.
#
# Uso:
#   ./scripts/backup_db.sh
#
# Pensado para correr por cron en el servidor (ver DEPLOY.md, sección
# "Backups"). Es idempotente y seguro de correr a mano en cualquier momento:
# BACKUP DATABASE no bloquea la base ni interrumpe a los usuarios.
#
# Por qué hace un "docker cp" en vez de escribir directo al host:
# el servicio sqlserver de docker-compose.prod.yml monta únicamente el volumen
# nombrado portal_ideas_sqlserver_data en /var/opt/mssql. No hay bind-mount al
# host, así que SQL Server solo puede escribir dentro del contenedor. El backup
# se hace primero a /tmp del contenedor (capa escribible, NO el volumen) y de
# ahí se copia al host. Eso cumple el requisito de que el backup sobreviva
# aunque se borre el volumen de datos.
#
# Alternativa futura: agregar un bind-mount (./backups:/backups) al servicio
# sqlserver y escribir directo. Es más limpio, pero exige recrear el contenedor.

set -euo pipefail

# --- Configuración (sobreescribible por variable de entorno) -----------------
CONTENEDOR="${CONTENEDOR:-portal-ideas-sqlserver}"
BASE_DATOS="${BASE_DATOS:-portafolio_iniciativas_anc}"
DIR_BACKUPS="${DIR_BACKUPS:-/opt/portal-ideas-anc/backups}"
ARCHIVO_LOG="${ARCHIVO_LOG:-${DIR_BACKUPS}/backup.log}"
DIAS_RETENCION="${DIAS_RETENCION:-14}"

SQLCMD=/opt/mssql-tools18/bin/sqlcmd

MARCA=$(date +%Y-%m-%d_%H%M)
NOMBRE="backup_${MARCA}.bak"
RUTA_TMP="/tmp/${NOMBRE}"
RUTA_HOST="${DIR_BACKUPS}/${NOMBRE}"

mkdir -p "$DIR_BACKUPS"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $*" | tee -a "$ARCHIVO_LOG"; }

# Cualquier fallo (set -e) pasa por acá antes de salir, así que el log siempre
# queda con el motivo y cron manda el mensaje por correo si está configurado.
on_error() {
    log "ERROR: el backup FALLÓ en la línea $1. No se generó ${NOMBRE}."
    docker exec "$CONTENEDOR" rm -f "$RUTA_TMP" 2>/dev/null || true
    exit 1
}
trap 'on_error $LINENO' ERR

log "=== Inicio del backup de ${BASE_DATOS} ==="

# El contenedor tiene que estar corriendo; si no, fallamos con un mensaje claro
# en vez de con un error críptico de docker exec.
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTENEDOR"; then
    log "ERROR: el contenedor '${CONTENEDOR}' no está corriendo."
    exit 1
fi

# La contraseña de sa se lee del propio contenedor en vez de duplicarla acá o
# leer el .env: es la misma que compose ya le inyectó, y así este script no
# necesita conocer ningún secreto. Se pasa por SQLCMDPASSWORD y no por -P para
# que no quede visible en la lista de procesos del contenedor.
PASSWORD_SA=$(docker exec "$CONTENEDOR" printenv MSSQL_SA_PASSWORD)

ejecutar_sql() {
    docker exec -e SQLCMDPASSWORD="$PASSWORD_SA" "$CONTENEDOR" \
        "$SQLCMD" -C -S localhost -U sa -b -Q "$1"
}

log "1/4 Generando el backup dentro del contenedor..."
# Sin COMPRESSION a propósito: es una feature de Standard/Enterprise y en
# Express falla con "BACKUP DATABASE WITH COMPRESSION is not supported on
# Express Edition". Producción corre Express (ver docker-compose.prod.yml).
# El backup sin comprimir pesa aproximadamente lo mismo que la base (~16 MB
# hoy), así que 14 días de retención ocupan un espacio despreciable.
ejecutar_sql "BACKUP DATABASE [${BASE_DATOS}] TO DISK = N'${RUTA_TMP}' WITH INIT, STATS = 25;" \
    2>&1 | sed 's/^/       /' | tee -a "$ARCHIVO_LOG"

# Un backup que no se puede restaurar no sirve de nada. VERIFYONLY lee el
# archivo entero y valida checksums sin restaurar: es barato y detecta acá
# mismo un backup corrupto, en vez de dentro de seis meses durante una
# emergencia.
log "2/4 Verificando la integridad del backup..."
ejecutar_sql "RESTORE VERIFYONLY FROM DISK = N'${RUTA_TMP}';" \
    2>&1 | sed 's/^/       /' | tee -a "$ARCHIVO_LOG"

log "3/4 Copiando al host (${RUTA_HOST})..."
docker cp "${CONTENEDOR}:${RUTA_TMP}" "$RUTA_HOST"
docker exec "$CONTENEDOR" rm -f "$RUTA_TMP"

if [ ! -s "$RUTA_HOST" ]; then
    log "ERROR: ${RUTA_HOST} quedó vacío o no existe."
    exit 1
fi
TAMANO=$(du -h "$RUTA_HOST" | cut -f1)

log "4/4 Borrando backups de más de ${DIAS_RETENCION} días..."
# El -newer protege al backup más reciente: si el cron se detiene por más de
# DIAS_RETENCION días, sin esta guarda TODOS los backups quedarían vencidos y
# se borrarían de una, dejando cero copias justo cuando más se necesitan.
BORRADOS=0
while IFS= read -r viejo; do
    [ -z "$viejo" ] && continue
    rm -f "$viejo"
    log "       borrado: $(basename "$viejo")"
    BORRADOS=$((BORRADOS + 1))
done < <(find "$DIR_BACKUPS" -maxdepth 1 -name 'backup_*.bak' -type f \
             -mtime "+${DIAS_RETENCION}" ! -newer "$RUTA_HOST" ! -samefile "$RUTA_HOST" 2>/dev/null)

TOTAL=$(find "$DIR_BACKUPS" -maxdepth 1 -name 'backup_*.bak' -type f | wc -l)
log "OK: ${NOMBRE} (${TAMANO}) — ${BORRADOS} vencido(s) borrado(s), ${TOTAL} backup(s) en total."
log "=== Fin del backup ==="
