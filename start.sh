#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Loading base fixtures..."
python manage.py base_loaddata

echo "Regenerating brand favicons..."
# ponytail: full regen per deploy is fine while brand count is small; add --missing-only if startup cost ever matters
python manage.py backfill_brand_favicons

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:80 project.wsgi:application
