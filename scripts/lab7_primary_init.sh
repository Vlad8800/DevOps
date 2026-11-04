#!/bin/sh
set -eu

# Only runs for newly initialized Docker volumes. The PowerShell helper applies
# the same rule to already existing primary volumes.
rule='host replication postgres all scram-sha-256'
grep -qxF "$rule" "$PGDATA/pg_hba.conf" || printf '%s\n' "$rule" >> "$PGDATA/pg_hba.conf"
if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    pg_ctl -D "$PGDATA" reload
fi
