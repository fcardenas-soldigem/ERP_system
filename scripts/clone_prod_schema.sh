#!/usr/bin/env bash
#
# Clona el ESQUEMA de producción (Supabase) + la tabla django_migrations hacia la
# BD Postgres LOCAL de docker-compose.
#
#   - SOLO LECTURA sobre producción (únicamente pg_dump).
#   - NO copia datos de clientes: solo el schema `public` y la data de
#     django_migrations (para que `migrate` local diga "No migrations to apply").
#   - Los dumps van a $TMPDIR (/tmp); NUNCA se commitean.
#   - Usa la imagen postgres:17 para igualar el major de prod (Supabase 17).
#
# Uso:  ./scripts/clone_prod_schema.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f $REPO_ROOT/docker-compose.yml"
ENV_PROD="$REPO_ROOT/backend/.env.production"
PG_IMAGE="postgres:17"

[ -f "$ENV_PROD" ] || { echo "ERROR: falta $ENV_PROD"; exit 1; }

read_var() { grep "^$1=" "$ENV_PROD" | head -1 | cut -d= -f2-; }
PGPASSWORD_PROD="$(read_var DB_PASSWORD)"
PHOST="$(read_var DB_HOST)"; PPORT="$(read_var DB_PORT)"
PUSER="$(read_var DB_USER)"; PNAME="$(read_var DB_NAME)"

SCHEMA_SQL="${TMPDIR:-/tmp}/erp_schema.sql"
MIG_SQL="${TMPDIR:-/tmp}/erp_migrations_data.sql"

echo "[1/4] Levantando BD local (docker compose db)..."
$COMPOSE up -d db
until $COMPOSE exec -T db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done

echo "[2/4] Volcando schema public + django_migrations desde prod (solo lectura)..."
docker run --rm -e PGPASSWORD="$PGPASSWORD_PROD" -e PGSSLMODE=require "$PG_IMAGE" \
  pg_dump -h "$PHOST" -p "$PPORT" -U "$PUSER" -d "$PNAME" \
  --schema=public --schema-only --no-owner --no-privileges > "$SCHEMA_SQL"
docker run --rm -e PGPASSWORD="$PGPASSWORD_PROD" -e PGSSLMODE=require "$PG_IMAGE" \
  pg_dump -h "$PHOST" -p "$PPORT" -U "$PUSER" -d "$PNAME" \
  --data-only -t public.django_migrations --no-owner --no-privileges > "$MIG_SQL"

echo "[3/4] Reseteando schema public local (idempotente) y cargando..."
# Solo la BD LOCAL erp: deja el clon limpio y evita duplicar django_migrations
# (COPY appendería) al re-ejecutar el script.
$COMPOSE exec -T db psql -U postgres -d erp -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" >/dev/null
$COMPOSE exec -T db psql -U postgres -d erp -v ON_ERROR_STOP=0 < "$SCHEMA_SQL" >/dev/null
$COMPOSE exec -T db psql -U postgres -d erp -v ON_ERROR_STOP=0 < "$MIG_SQL" >/dev/null

echo "[4/4] Verificando (debe decir 'No migrations to apply')..."
( cd "$REPO_ROOT/backend" && source ../venv/bin/activate && python manage.py migrate --skip-checks )

echo
echo "OK. Dumps temporales en:"
echo "  $SCHEMA_SQL"
echo "  $MIG_SQL"
echo "NO los commitees. Podés borrarlos con: rm -f \"$SCHEMA_SQL\" \"$MIG_SQL\""
