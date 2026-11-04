#!/bin/sh
set -eu

: "${PRIMARY_HOST:?PRIMARY_HOST is required}"
: "${REPLICA_NAME:?REPLICA_NAME is required}"
: "${PGPASSWORD:?PGPASSWORD is required}"

mkdir -p "$PGDATA"
chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    su-exec postgres pg_basebackup \
        -h "$PRIMARY_HOST" -U postgres -D "$PGDATA" -Fp -Xs -R
    printf "primary_conninfo = 'host=%s port=5432 user=postgres password=%s application_name=%s'\n" \
        "$PRIMARY_HOST" "$PGPASSWORD" "$REPLICA_NAME" \
        >> "$PGDATA/postgresql.auto.conf"
fi

exec su-exec postgres postgres -D "$PGDATA" -c hot_standby=on
