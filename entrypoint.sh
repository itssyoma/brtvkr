#!/bin/sh
set -e

python manage.py migrate
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --log-level "${GUNICORN_LOG_LEVEL:-info}"
