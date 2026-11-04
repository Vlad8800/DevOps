$ErrorActionPreference = 'Stop'

$compose = @('-f', 'docker-compose.lab7.yml', '-f', 'docker-compose.lab7.replication.yml')

docker compose @compose up -d --wait shard_a shard_b
if ($LASTEXITCODE -ne 0) { throw 'Could not start primary shards.' }

foreach ($shard in @('shard_a', 'shard_b')) {
    docker compose @compose exec -T -u postgres $shard sh /docker-entrypoint-initdb.d/10-replication.sh
    if ($LASTEXITCODE -ne 0) { throw "Could not configure replication on $shard." }
}

docker compose @compose up -d --wait shard_a_replica shard_b_replica
if ($LASTEXITCODE -ne 0) { throw 'Could not start replicas.' }

docker compose @compose ps
if ($LASTEXITCODE -ne 0) { throw 'Could not read Compose status.' }

foreach ($shard in @('shard_a', 'shard_b')) {
    Write-Output "Replication from $shard"
    docker compose @compose exec -T $shard psql -U postgres -d lab7 -c 'select application_name, state, sync_state from pg_stat_replication'
    if ($LASTEXITCODE -ne 0) { throw "Could not verify replication on $shard." }
}
