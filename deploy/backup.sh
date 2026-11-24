#!/usr/bin/env bash
# Nightly PostgreSQL backup. Keeps the last 14 days.
#
# Install:
#   sudo mkdir -p /var/backups/shortener && sudo chown postgres: /var/backups/shortener
#   sudo cp deploy/backup.sh /usr/local/bin/shortener-backup && sudo chmod +x /usr/local/bin/shortener-backup
#   sudo crontab -u postgres -e     ->   0 2 * * * /usr/local/bin/shortener-backup
#
# Restore:
#   gunzip -c /var/backups/shortener/shortener-YYYY-MM-DD.sql.gz | sudo -u postgres psql shortener
set -euo pipefail

DB_NAME="${DB_NAME:-shortener}"
DIR="${BACKUP_DIR:-/var/backups/shortener}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$DIR"
OUT="$DIR/shortener-$(date +%F).sql.gz"
pg_dump "$DB_NAME" | gzip > "$OUT"
chmod 600 "$OUT"
find "$DIR" -name 'shortener-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "Backup written: $OUT"
