#!/bin/bash
set -e

SRC="/opt/bots/tarot_bot"
DST="/opt/backups/arcanum"
REMOTE="gdrive:ArcanumBackups"
DATE=$(date +%F_%H-%M-%S)

mkdir -p "$DST"

DB_BACKUP="$DST/database_$DATE.db"
ENV_BACKUP="$DST/env_$DATE.bak"

sqlite3 "$SRC/data/database.db" ".backup '$DB_BACKUP'"
cp "$SRC/.env" "$ENV_BACKUP"

rclone copy "$DB_BACKUP" "$REMOTE/database" --create-empty-src-dirs
rclone copy "$ENV_BACKUP" "$REMOTE/env" --create-empty-src-dirs

find "$DST" -type f -mtime +30 -delete

echo "Backup created and uploaded to Google Drive: $DATE"
