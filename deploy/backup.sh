#!/usr/bin/env bash
# SQLite 备份：保留最近 14 天
set -euo pipefail

APP_DIR=/opt/breast-cancer-detection
BACKUP_DIR=/var/backups/breast-cancer
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# .backup 对运行中的 SQLite 是安全的（比直接 cp 好）
sqlite3 "$APP_DIR/admin_backend/instance/admin.db" ".backup '$BACKUP_DIR/admin-$STAMP.db'"
[[ -f "$APP_DIR/agent.db" && -s "$APP_DIR/agent.db" ]] && \
  sqlite3 "$APP_DIR/agent.db" ".backup '$BACKUP_DIR/agent-$STAMP.db'"

find "$BACKUP_DIR" -name '*.db' -mtime +14 -delete

echo "备份完成: $BACKUP_DIR ($STAMP)"
