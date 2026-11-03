#!/usr/bin/env bash
# Testy API w kontenerach: osobny Postgres 15 + Python 3.11. Sprząta po sobie.
set -euo pipefail
cd "$(dirname "$0")"
NET=ikzocr_tests_net; PG=ikzocr_tests_pg
# Domyślnie czysty Python 3.11; offline można podać lokalny obraz, np. TEST_IMAGE=ikzocr-test:latest
IMAGE="${TEST_IMAGE:-python:3.11-slim}"
cleanup() { docker rm -f "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_USER=medyk -e POSTGRES_PASSWORD=medyk \
  -e POSTGRES_DB=medykocr_test postgres:15-alpine >/dev/null
until docker exec "$PG" pg_isready -U medyk -d medykocr_test >/dev/null 2>&1; do sleep 1; done
sleep 1
docker run --rm --network "$NET" -v "$PWD/..:/repo" -w /repo/api \
  -e TEST_DATABASE_URL="postgresql://medyk:medyk@$PG:5432/medykocr_test" \
  --entrypoint sh "$IMAGE" -c "pip install -q --root-user-action=ignore -r requirements.ci.txt && python -m pytest -q $*"
