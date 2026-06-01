#!/bin/sh
set -e

# Wait for Postgres to accept connections before migrating.
echo "Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} ..."
until python -c "import socket,os,sys; s=socket.socket(); s.settimeout(2); \
    s.connect((os.environ.get('POSTGRES_HOST','db'), int(os.environ.get('POSTGRES_PORT','5432')))); s.close()" 2>/dev/null; do
  sleep 1
done
echo "Postgres is up."

python manage.py migrate --noinput

exec "$@"
