#!/bin/sh
# Make the mounted folders writable by the app user, then drop root and start.
# (Docker creates missing bind-mount folders as root.) Skipped when the container
# is already started as a non-root user, e.g. with `user:` in docker-compose.yml.
set -e
if [ "$(id -u)" = "0" ]; then
  for d in /output /server-missions; do
    [ -d "$d" ] && chown -R app:app "$d" 2>/dev/null || true
  done
  # setpriv keeps the environment, so point HOME at the app user's own home
  # (pydcs looks for "~/Saved Games").
  export HOME=/home/app USER=app LOGNAME=app
  exec setpriv --reuid=app --regid=app --init-groups "$@"
fi
exec "$@"
