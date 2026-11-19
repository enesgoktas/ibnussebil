#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

DB_FILE="$ROOT_DIR/data/ibnussebil.db"
if [ ! -f "$DB_FILE" ]; then
  echo "DB bulunamadı: $DB_FILE"
  exit 1
fi

STAMP="$(date +%Y-%m-%d-%H%M)"
TARGET="$BACKUP_DIR/ibnussebil-$STAMP.db"

python3 - "$DB_FILE" "$TARGET" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
source.backup(target)
target.close()
source.close()
PY

find "$BACKUP_DIR" -name 'ibnussebil-*.db' -mtime +14 -delete
echo "Yedek hazır: $TARGET"
