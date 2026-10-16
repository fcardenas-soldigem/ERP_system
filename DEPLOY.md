# Despliegue del backend (Cloud Run) — flujo real

Release de `sec/aislamiento-tenants` (aislamiento multi-empresa + MCP base + errores
genéricos + logging JSON). Todo lo de abajo se ejecuta **a mano, desde local**; nada
de este documento se ha ejecutado todavía. Reglas: no hay secretos en archivos del
repo; se leen del entorno o de Secret Manager.

| Parámetro | Valor |
|---|---|
| Proyecto GCP | `erp-system-468516` |
| Región | `southamerica-west1` |
| Servicio Cloud Run | `erp-backend` |
| Imagen (Artifact Registry) | `southamerica-west1-docker.pkg.dev/erp-system-468516/erp-repo/erp-backend` |
| Job de migraciones | `erp-migrate` (se crea en §4 la primera vez) |
| BD producción | Supabase (Postgres). Credenciales en `backend/.env.production` (**gitignored**) |

```bash
# Variables comunes para toda la sesión de deploy
export PROJECT=erp-system-468516 REGION=southamerica-west1 SERVICE=erp-backend
export IMAGE=southamerica-west1-docker.pkg.dev/$PROJECT/erp-repo/erp-backend
export TAG=$(git rev-parse --short HEAD)          # tag inmutable = commit desplegado
gcloud config set project $PROJECT
```

## 0. Pre-deploy (local)

```bash
cd backend && source venv/bin/activate
python manage.py test --settings=config.settings_test_pg --noinput   # Postgres local :5433
python manage.py makemigrations --check --dry-run                     # "No changes detected"
python manage.py check --deploy --settings=config.settings            # con DJANGO_DEBUG=False
cd ..
```

Comprobar también que `backend/.env.local` apunta a `localhost:5433` (los tests nunca
deben tocar Supabase; `settings_test_pg` hereda de `.env.local`).

## 1. Backup de la BD de producción (obligatorio antes de migrar)

`pg_dump` lee las credenciales **del entorno**, nunca escritas en este archivo. Supabase:
usar el host/puerto de **sesión directa (5432)**, no el pooler en modo transacción (6543),
que no soporta `pg_dump`.

```bash
mkdir -p backups && chmod 700 backups
set -a; source backend/.env.production; set +a          # exporta DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
[ -n "$DB_HOST" ] || { echo "DB_HOST vacío"; exit 1; }
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom --no-owner --no-privileges \
  --file "backups/erp_prod_$(date +%Y%m%d_%H%M)_pre_${TAG}.dump"
ls -lh backups/ | tail -1
unset DB_PASSWORD PGPASSWORD                              # no dejar la clave en el shell
```

Restaurar (solo si hace falta): `pg_restore --clean --if-exists --no-owner -d "$DB_NAME" -h ... backups/<archivo>.dump`.
`backups/` y `*.dump` están en `.gitignore`/`.gcloudignore`; no subirlos.

## 2. Build con tag inmutable (sin secretos)

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_TAG=$TAG .
```

- `cloudbuild.yaml` etiqueta `${IMAGE}:${TAG}` **y** `:latest`.
- El `Dockerfile` declara `ARG DJANGO_SECRET_KEY=dummy-...` etc. **solo** para que
  `collectstatic` arranque en build. No pasar `--build-arg` con valores reales. Los
  secretos reales llegan al contenedor desde Secret Manager (§3).
- `.gcloudignore` excluye `backend/media/`, `*.sql`, `*.dump`, `*.md`, `frontend/`.

## 3. Verificar el digest y preparar secretos

```bash
DIGEST=$(gcloud artifacts docker images describe $IMAGE:$TAG --format='value(image_summary.digest)')
echo "$IMAGE@$DIGEST"      # ← desplegar SIEMPRE por digest, no por tag
```

Secretos (una sola vez; después solo `versions add`). Nombres en Secret Manager:

| Secreto | Variable en el contenedor |
|---|---|
| `django-secret-key` | `DJANGO_SECRET_KEY` |
| `jwt-signing-key` | `JWT_SIGNING_KEY` |
| `apis-net-pe-token` | `APIS_NET_PE_TOKEN` |
| `db-password` | `DB_PASSWORD` |
| `redis-url` (opcional) | `REDIS_URL` |

```bash
# Crear/rotar (lee de stdin; nunca del historial):
read -s -p "valor: " V && echo -n "$V" | gcloud secrets versions add django-secret-key --data-file=- ; unset V
# Permiso de lectura para la SA del servicio (una vez por secreto):
gcloud secrets add-iam-policy-binding django-secret-key \
  --member="serviceAccount:25656632090-compute@developer.gserviceaccount.com" --role=roles/secretmanager.secretAccessor
```

Variables **no secretas** (van con `--set-env-vars` o un archivo YAML fuera del repo, p. ej. `/tmp/erp-env-vars.yaml`):
`DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DB_NAME`, `DB_USER`,
`DB_HOST`, `DB_PORT`, `GS_BUCKET_NAME`, `GS_PROJECT_ID`, `LOG_FORMAT=json` (es el valor por
defecto con `DJANGO_DEBUG=False`; se deja explícito).

```bash
export SECRETS="DJANGO_SECRET_KEY=django-secret-key:latest,JWT_SIGNING_KEY=jwt-signing-key:latest,APIS_NET_PE_TOKEN=apis-net-pe-token:latest,DB_PASSWORD=db-password:latest"
# Si hay Redis:  SECRETS="$SECRETS,REDIS_URL=redis-url:latest"
# Asistente IA (OBLIGATORIO si el chat está habilitado). `--set-secrets` y
# `--env-vars-file` REEMPLAZAN todo el entorno de la revisión: si se omiten,
# el chat responde 503 "asistente no configurado" (antes: 500). Crear los
# secretos openai-api-key / openai-assistant-id igual que en §3.
SECRETS="$SECRETS,OPENAI_API_KEY=openai-api-key:latest,OPENAI_ASSISTANT_ID=openai-assistant-id:latest"
# Si se usa el analista con Claude:  SECRETS="$SECRETS,CLAUDE_API_KEY=claude-api-key:latest"
```

## 4. Migraciones con un Cloud Run Job (antes de mover tráfico)

Las migraciones de este release son **aditivas** (ver §8): el código viejo sigue
funcionando con el esquema nuevo, así que se migra primero y se despliega después.

```bash
# Primera vez: create. Siguientes: update (misma línea con "update").
gcloud run jobs create erp-migrate \
  --image "$IMAGE@$DIGEST" --region $REGION \
  --command python --args manage.py,migrate,--noinput \
  --env-vars-file /tmp/erp-env-vars.yaml --set-secrets "$SECRETS" \
  --max-retries 0 --task-timeout 15m

gcloud run jobs execute erp-migrate --region $REGION --wait
gcloud run jobs executions list --job erp-migrate --region $REGION --limit 1   # Succeeded
```

Si falla: NO desplegar. El job no deja la BD a medias (cada migración corre en su
transacción). Revisar logs: `gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="erp-migrate"' --limit 50`.

## 5. Deploy sin tráfico + canary

```bash
PREV=$(gcloud run services describe $SERVICE --region $REGION --format='value(status.latestReadyRevisionName)')
echo "Revisión actual (para rollback): $PREV"

gcloud run deploy $SERVICE \
  --image "$IMAGE@$DIGEST" --region $REGION \
  --env-vars-file /tmp/erp-env-vars.yaml --set-secrets "$SECRETS" \
  --no-traffic --tag canary \
  --min-instances 0 --max-instances 3 --cpu 1 --memory 1Gi --timeout 120

CANARY_URL=$(gcloud run services describe $SERVICE --region $REGION --format='value(status.traffic[?tag=canary].url)' | head -1)
curl -fsS "$CANARY_URL/api/health/"                                 # {"status":"ok"}
curl -sS -o /dev/null -w '%{http_code}\n' "$CANARY_URL/api/ventas/"   # 401 (sin token) — nunca 500
```

Canary al 10 %, observar 10–15 min (5xx, latencia, logs JSON con `severity=ERROR`):

```bash
gcloud run services update-traffic $SERVICE --region $REGION --to-tags canary=10
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE AND severity>=ERROR" --freshness=15m --limit 50
```

Promover al 100 % cuando esté limpio:

```bash
gcloud run services update-traffic $SERVICE --region $REGION --to-latest
gcloud run services update-traffic $SERVICE --region $REGION --remove-tags canary
```

## 6. Verificación manual post-deploy (ver también REVIEW_SEC.md §4)

1. Login con un usuario real → `/api/auth/profile/` muestra su empresa.
2. Dashboard, ventas, compras, productos, proveedores cargan (y con Redis: segunda carga
   más rápida, mismos datos).
3. Crear un producto → aparece en la lista inmediatamente (invalidación de caché).
4. Error forzado (p. ej. `GET /api/compras/compras/999999/`) → `{"detail": "No encontrado"}`
   o 404, nunca un traceback ni `str(e)`.
5. Logs en Cloud Logging con `jsonPayload.empresa_id`, `jsonPayload.user_id`, `jsonPayload.request_id`.
6. `POST /api/mcp/` sin token → 401; con token de la UI "Conectar Claude" → `tools/list`.
7. Login de un usuario sin empresa → 403 (no entra a Soldigem).

## 7. Rollback

```bash
# Tráfico de vuelta a la revisión anterior (segundos, sin rebuild):
gcloud run services update-traffic $SERVICE --region $REGION --to-revisions $PREV=100
```

- La migración `agente/0001` puede quedarse aplicada: el código anterior no toca esas
  tablas. Si se quiere revertir el esquema: `gcloud run jobs update erp-migrate ... --args manage.py,migrate,agente,zero`
  y ejecutar; o desde local con `DOTENV_FILE=.env.production python manage.py migrate agente zero`.
- Si algo tocó datos: restaurar el dump de §1 con `pg_restore` (último recurso; coordinar
  parada de escritura).

## 8. Migraciones de este release (vs `main`)

Ver la sección "Migraciones nuevas vs main" más abajo (C2).

## 9. Referencia: release anterior (media en GCS)

La migración de media a GCS (`migrar_media_a_gcs`, `auditar_archivos`) ya está en `main`;
el procedimiento detallado quedó en el historial de git de este archivo
(`git show 9bc27e4:DEPLOY.md`). Resumen: `GS_BUCKET_NAME` + `GS_PROJECT_ID` activan GCS
con URLs firmadas v4 vía IAM `signBlob`; sin esas variables se usa disco local (dev).

---

## Migraciones nuevas vs `main` (C2)

`git diff --name-status main...HEAD -- 'backend/apps/*/migrations/*.py'` y
`makemigrations --check --dry-run` → **No changes detected** (no hay cambios de modelo sin migración).

| Migración | Operaciones | ¿Reversible? | ¿Bloquea tablas existentes? | ¿Añade NOT NULL sin default a tabla existente? |
|---|---|---|---|---|
| `agente/0001_initial` | `CreateModel ApiToken` (FK → `empresas_empresa` CASCADE, FK → usuario SET_NULL, `token_hash` unique), `CreateModel AgenteAccionLog` (FK → empresa, FK → apitoken), `AddIndex token_hash` | **Sí** (`migrate agente zero` borra las dos tablas; no hay datos que preservar) | **No**: `CREATE TABLE`/`CREATE INDEX` sobre tablas nuevas y vacías. Las FK toman un lock breve (`SHARE ROW EXCLUSIVE`) sobre `empresas_empresa` y `authentication_customuser` solo durante el `ADD CONSTRAINT` (milisegundos: la tabla referenciante está vacía) | **No**: todas las columnas NOT NULL (`empresa`, `nombre`, `token_hash`, …) nacen con la tabla; no se altera ninguna tabla existente. La lección de `ventas/0019` (NOT NULL nuevo en tabla existente deja sin DEFAULT físico al código viejo) **no aplica** |

Conclusión: migración puramente aditiva → se puede aplicar **antes** del deploy y el
código de la revisión anterior sigue funcionando durante el canary. Depende de
`empresas/0008_alter_empresa_firma_aprobado_and_more`, que ya está en `main`.

Cambios de **datos** sin migración: ninguno. Cambios de comportamiento que afectan a
filas existentes: ninguno (el login ya no asigna empresa a usuarios huérfanos; si en
prod existiera un usuario con `empresa=NULL`, dejará de poder entrar hasta asignarle
empresa en el admin — revisar con `SELECT id FROM authentication_customuser WHERE empresa_id IS NULL;`
antes del deploy).
