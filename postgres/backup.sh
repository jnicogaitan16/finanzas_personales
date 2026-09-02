#!/bin/sh
# Backup automático de la base de datos finanzas
# Se ejecuta desde el servicio db-backup en Docker Compose

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="finanzas_${TIMESTAMP}.sql.gz"
KEEP_DAYS=${BACKUP_RETENTION_DAYS:-7}

echo "[$(date)] Iniciando backup de finanzas..."

pg_dump -h postgres -U evolution finanzas | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "[$(date)] Backup creado: ${FILENAME} ($(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1))"

# Limpiar backups viejos
DELETED=$(find "${BACKUP_DIR}" -name "finanzas_*.sql.gz" -mtime +${KEEP_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
  echo "[$(date)] Eliminados ${DELETED} backups con mas de ${KEEP_DAYS} dias"
fi

echo "[$(date)] Backup completado"
