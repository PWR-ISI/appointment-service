#!/usr/bin/env sh
set -e

DB_HOST="${DJANGO_DB_HOST:-${DB_HOST:-db}}"
DB_PORT="${DJANGO_DB_PORT:-${DB_PORT:-5432}}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT}..."
until nc -z "${DB_HOST}" "${DB_PORT}"; do
  sleep 1
done
echo "Database is up."

python manage.py makemigrations appointments --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec "$@"
