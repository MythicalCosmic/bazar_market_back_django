#!/bin/sh
set -e

echo "Waiting for postgres..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('${DB_HOST:-db}', ${DB_PORT:-5432}))
    s.close()
except: exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL ready"

# Only the migrator container should run migrations. Set RUN_MIGRATIONS=1 there.
# Default: web service migrates on first boot in dev; in prod, run a dedicated job.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
