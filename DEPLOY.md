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

Secretos (una sola vez; después solo `versions add`). En Secret Manager cada secreto
se llama **igual que su variable, en mayúsculas** (convención de prod):

| Secreto | Variable en el contenedor |
|---|---|
| `DJANGO_SECRET_KEY` | `DJANGO_SECRET_KEY` |
| `JWT_SIGNING_KEY` | `JWT_SIGNING_KEY` |
| `APIS_NET_PE_TOKEN` | `APIS_NET_PE_TOKEN` |
| `DB_PASSWORD` | `DB_PASSWORD` |
| `REDIS_URL` (opcional) | `REDIS_URL` |

```bash
# Crear/rotar (lee de stdin; nunca del historial):
read -s -p "valor: " V && echo -n "$V" | gcloud secrets versions add DJANGO_SECRET_KEY --data-file=- ; unset V
# Permiso de lectura para la SA del servicio (una vez por secreto):
gcloud secrets add-iam-policy-binding DJANGO_SECRET_KEY \
  --member="serviceAccount:25656632090-compute@developer.gserviceaccount.com" --role=roles/secretmanager.secretAccessor
```

Variables **no secretas** (van con `--set-env-vars` o un archivo YAML fuera del repo, p. ej. `/tmp/erp-env-vars.yaml`):
`DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DB_NAME`, `DB_USER`,
`DB_HOST`, `DB_PORT`, `GS_BUCKET_NAME`, `GS_PROJECT_ID`, `LOG_FORMAT=json` (es el valor por
defecto con `DJANGO_DEBUG=False`; se deja explícito).

```bash
export SECRETS="DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest,JWT_SIGNING_KEY=JWT_SIGNING_KEY:latest,APIS_NET_PE_TOKEN=APIS_NET_PE_TOKEN:latest,DB_PASSWORD=DB_PASSWORD:latest"
# Si hay Redis:  SECRETS="$SECRETS,REDIS_URL=REDIS_URL:latest"
# El asistente IA (Jorge, ventas, compras) NO usa secretos: ver §3.1 (Vertex AI + ADC).
```

### 3.1 Asistente IA: Vertex AI con la identidad del servicio (sin API key)

Desde `feat/llm-agnostico` el chat corre sobre Gemini en Vertex AI con las
credenciales por defecto (ADC) de la cuenta de servicio de Cloud Run. **No hay
`OPENAI_*` ni ninguna clave de IA en Secret Manager.** Si falta el permiso o el
modelo, el chat responde 503 "asistente no configurado"; si Vertex falla o tarda
más de `LLM_TIMEOUT`, 502. Nunca 500 ni traceback.

Variables no secretas (añadir a `/tmp/erp-env-vars.yaml`):

| Variable | Valor en prod | Notas |
|---|---|---|
| `LLM_PROVIDER` | `vertex` | `openai` = cualquier API `chat.completions` (requiere `LLM_BASE_URL` + secreto `LLM_API_KEY`) |
| `LLM_MODEL` | `gemini-3.1-flash-lite` | GA desde 2026-05-07 (retiro ≥ 2027-05-07). `gemini-2.5-flash-lite` se retira el **2026-10-20**: no usar |
| `LLM_LOCATION` | `global` | `gemini-3.1-flash-lite` solo existe en `global`, `us` y `eu` (no hay región única ni Sudamérica) |
| `LLM_PROJECT` | `erp-system-468516` | por defecto toma `GS_PROJECT_ID` |
| `LLM_TIMEOUT` | `30` | segundos; al excederse → 502 |
| `LLM_HISTORIAL_N` | `20` | mensajes de contexto por turno (≈10 interacciones) |
| `LLM_WRITE_TOOLS` | `false` | `crear_venta`/`crear_compra` fuera del schema del modelo y rechazadas por el ejecutor. Activar solo cuando exista confirmación en la UI |

#### Lista exacta de entorno para desplegar esta rama (`feat/llm-agnostico`)

Archivo `/tmp/erp-env-vars.yaml` completo (valores no secretos; sustituir solo `<…>`):

```yaml
DJANGO_DEBUG: "False"
DJANGO_ALLOWED_HOSTS: "erp-backend-25656632090.southamerica-west1.run.app,erp.soldigem.com.pe"
CORS_ALLOWED_ORIGINS: "https://erp.soldigem.com.pe"
DB_NAME: "postgres"
DB_USER: "<usuario de Supabase>"
DB_HOST: "<host de Supabase>.supabase.com"
DB_PORT: "5432"
GS_BUCKET_NAME: "<bucket de media>"
GS_PROJECT_ID: "erp-system-468516"
GS_SA_EMAIL: "25656632090-compute@developer.gserviceaccount.com"
LOG_FORMAT: "json"
LLM_PROVIDER: "vertex"
LLM_MODEL: "gemini-3.1-flash-lite"
LLM_LOCATION: "global"
LLM_PROJECT: "erp-system-468516"
LLM_TIMEOUT: "30"
LLM_HISTORIAL_N: "20"
LLM_WRITE_TOOLS: "false"
```

Secretos (Secret Manager → variable), sin ninguna clave de IA:

```bash
export SECRETS="DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest,JWT_SIGNING_KEY=JWT_SIGNING_KEY:latest,APIS_NET_PE_TOKEN=APIS_NET_PE_TOKEN:latest,DB_PASSWORD=DB_PASSWORD:latest"
# Si hay Redis:  SECRETS="$SECRETS,REDIS_URL=REDIS_URL:latest"
```

Variables que **dejan de existir** y hay que quitar del servicio y de Secret Manager
(opcionalmente destruir las versiones): `OPENAI_API_KEY`, `OPENAI_ASSISTANT_ID`,
`OPENAI_MODEL`, `CLAUDE_API_KEY`, `VENTAS_ASSISTANT_ID`, `COMPRAS_ASSISTANT_ID`. No se usan
`LLM_BASE_URL` ni `LLM_API_KEY` salvo que `LLM_PROVIDER=openai`.

Permisos de la cuenta de servicio del servicio (`25656632090-compute@…`):
`roles/secretmanager.secretAccessor` (ya), `roles/aiplatform.user` (NUEVO), acceso al
bucket de media (ya). API a habilitar: `aiplatform.googleapis.com`.

IAM (una vez, con la SA del servicio; `aiplatform.user` incluye `aiplatform.endpoints.predict`):

```bash
gcloud services enable aiplatform.googleapis.com --project erp-system-468516
gcloud projects add-iam-policy-binding erp-system-468516 \
  --member="serviceAccount:25656632090-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Comprobación desde local con tu ADC (no toca prod):
`cd backend && LLM_PROJECT=erp-system-468516 python manage.py eval_llm --model gemini-3.1-flash-lite --solo q01`.

**Qué datos de clientes salen al modelo en cada tool.** El modelo recibe siempre:
nombre de la empresa, fecha, el texto que escribe el usuario y las últimas N
interacciones de SU conversación. Además, el resultado de cada tool que decida
llamar (datos de la empresa del usuario autenticado; nunca de otra):

| Perfil | Tool | Datos que viajan al modelo |
|---|---|---|
| Jorge | `analizar_ventas` | totales, nº de ventas y tendencias del período; top productos (nombre, SKU, cantidades, ingresos) |
| Jorge | `analizar_inventario` | nombre, SKU, stock actual/mínimo y categoría de productos (bajo stock y resumen) |
| Jorge | `analizar_clientes` | nombre del cliente, nº de compras y montos acumulados del período (sin documento ni contacto) |
| Jorge | `consulta_libre` | conteos de productos/clientes, razón social y RUC de proveedores, ventas recientes (cliente, total, fecha) |
| Ventas | `buscar_clientes` | nombre y documento (RUC/DNI) de los clientes que coinciden con la búsqueda |
| Ventas | `buscar_productos` | nombre, SKU, precio de venta y stock |
| Ventas | `crear_venta` | el resultado: número de venta, cliente, total; los argumentos los redacta el modelo con lo que el usuario dictó |
| Compras | `buscar_proveedores` | razón social y RUC de proveedores |
| Compras | `buscar_almacenes` | nombre y dirección de almacenes |
| Compras | `buscar_productos` | nombre, SKU, precio de compra |
| Compras | `crear_compra` | el resultado: número de compra, proveedor, total |

No viajan: contraseñas, tokens, emails/teléfonos de clientes (salvo que el usuario
los escriba), datos de otras empresas, ni el historial de otros usuarios. Vertex AI
(servicio de pago de Google Cloud) no usa los prompts para entrenar modelos y los
procesa en la ubicación del endpoint (`global` = sin garantía de región).

Tokens por empresa y día: tabla `ai_assistant_usollm` (`tokens_entrada`,
`tokens_salida`, `llamadas`, `modelo`). Costo de referencia (lista, 2026-10-16):
`gemini-3.1-flash-lite` $0,25 / $1,50 por 1M tokens de entrada / salida.

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
8. Asistente IA: `POST /api/ai/threads-tools/` → 200 con `thread_id`; enviar "¿qué
   productos tienen stock bajo?" → respuesta con productos reales de la empresa y una
   fila nueva/actualizada en `ai_assistant_usollm` (empresa, hoy, `LLM_MODEL`). Sin ADC o
   sin `roles/aiplatform.user` → 503, nunca 500. Revisar que Cloud Logging no contenga
   el texto del mensaje (solo `llm_call … tokens_in=… tokens_out=…`).

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

| `ai_assistant/0005_conversation_perfil_usollm_and_more` (feat/llm-agnostico) | `AddField Conversation.perfil` (varchar(10), `default='jorge'`), `CreateModel UsoLLM` (FK → empresa CASCADE), `AddConstraint unique(empresa, fecha, modelo)` | **Sí** (`migrate ai_assistant 0004`: borra la columna y la tabla; los datos de uso se pierden, las conversaciones no) | **No**: `ADD COLUMN … DEFAULT 'jorge' NOT NULL` en PostgreSQL ≥ 11 es solo metadato (sin reescritura), lock `ACCESS EXCLUSIVE` de milisegundos sobre `ai_assistant_conversation`; el resto son tablas nuevas | **No**: el NOT NULL llega con DEFAULT constante, el código viejo sigue insertando sin la columna |

Conclusión: migración puramente aditiva → se puede aplicar **antes** del deploy y el
código de la revisión anterior sigue funcionando durante el canary. Depende de
`empresas/0008_alter_empresa_firma_aprobado_and_more`, que ya está en `main`.

Cambios de **datos** sin migración: ninguno. Cambios de comportamiento que afectan a
filas existentes: ninguno (el login ya no asigna empresa a usuarios huérfanos; si en
prod existiera un usuario con `empresa=NULL`, dejará de poder entrar hasta asignarle
empresa en el admin — revisar con `SELECT id FROM authentication_customuser WHERE empresa_id IS NULL;`
antes del deploy).

## 10. Sesión en iPhone — MISMO ORIGEN vía rewrite de Vercel (0.3, revisado)

> Reemplaza el esquema anterior con un subdominio propio para la API:
> verificado en prod que ese subdominio responde `DEPLOYMENT_NOT_FOUND` de
> Vercel y **no llega al backend**. No crear dominios aparte para la API.

### Esquema

```
navegador ──► https://erp.soldigem.com.pe/api/…   (mismo origen que el SPA)
                 │  rewrite de Vercel (frontend/vercel.json)
                 ▼
              https://erp-backend-25656632090.southamerica-west1.run.app/api/…

navegador ──► Cloud Run DIRECTO solo para binarios (subidas y descargas PDF/Excel),
              autenticados con Bearer, sin cookie.

Telegram  ──► Cloud Run DIRECTO (/api/canales/telegram/)
```

La cookie `refresh_token` la emite, a ojos del navegador, `erp.soldigem.com.pe`:
es **first-party**, y Safari iOS deja de descartarla al reabrir la PWA.

### Qué cambia en Vercel (proyecto del ERP)

| Variable | Valor | Nota |
|---|---|---|
| `VITE_API_URL` | **vacío** (borrar la variable o dejarla en blanco) | NO `"/api"`: las rutas ya empiezan con `/api/` y quedaría `/api/api/` |
| `VITE_API_UPLOAD_URL` | `https://erp-backend-25656632090.southamerica-west1.run.app` | nueva: subidas y descargas binarias directo |

Las dos se inyectan en build: **requieren redeploy del frontend**.

`frontend/vercel.json` (ya en la rama):
- rewrite `/api/(.*)` → `https://erp-backend-…run.app/api/$1` **antes** del
  catch-all del SPA. Se usa `(.*)`→`$1` y no `/api/:path*`: `:path*` no captura la
  barra final y Django (`APPEND_SLASH`) respondería 301 a los POST sin barra.
- cabecera `x-vercel-enable-rewrite-caching: 0` en `/api/(.*)`: las respuestas
  de la API son por usuario y empresa; la CDN **nunca** debe cachearlas (los
  proyectos de Vercel creados desde abril de 2026 cachean rewrites externos por
  defecto según las cabeceras del origen).

### Qué cambia en Cloud Run (backend)

| Variable | Valor | Por qué |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | `erp-backend-25656632090.southamerica-west1.run.app,erp.soldigem.com.pe` | Vercel reenvía `X-Forwarded-Host: erp.soldigem.com.pe` y `USE_X_FORWARDED_HOST=True` hace que Django valide **ese** host: sin él, todo `/api/` por el rewrite da 400 (`DisallowedHost`). Probado en `tests/test_mismo_origen.py` |
| `REFRESH_COOKIE_DOMAIN` | **eliminar** si quedó de una versión anterior | ya no existe: la cookie es host-only por diseño |
| `API_BASE_URL` | `https://erp.soldigem.com.pe` (es el default) | base de los links firmados al PDF que comparte el bot |

Sin cambios, verificados: `CORS_ALLOWED_ORIGINS=https://erp.soldigem.com.pe`
(lo usan los binarios directos; se añadió `CORS_EXPOSE_HEADERS=content-disposition`
para que el Excel conserve su nombre) y `CSRF_TRUSTED_ORIGINS` (ya lista
`https://erp.soldigem.com.pe`, settings.py).

### Cookie `refresh_token`

`HttpOnly; Secure; SameSite=Lax; Path=/api/` y **sin `Domain`** (host-only de
erp.soldigem.com.pe). `apps/authentication/views.py::_cookie_kwargs`.
Login, refresh y logout usan los mismos atributos (si el path difiere, el
navegador no la borra).

### Límites de Vercel para el rewrite (docs oficiales, verificado 2026-10-27)

| Límite | Valor | Fuente | Impacto |
|---|---|---|---|
| Timeout del proxy | **120 s** (todos los planes) | vercel.com/docs/limits → «Proxied request timeout» | Holgado para el JSON de la API. Error si se excede: `ROUTER_EXTERNAL_TARGET_ERROR` |
| Body de request / respuesta en rewrites externos | **No documentado** | vercel.com/docs/rewrites no lo menciona; el 4,5 MB conocido es de Vercel Functions | Por eso los binarios **no** pasan por el rewrite |

Medido en local: PDF de cotización ≈ 3 KB sin logo y ≈ 1,3 MB con logo. Las
subidas admiten hasta 10 MB y las exportaciones Excel no tienen tope →
`frontend/src/lib/api.js` manda **todo** request con `FormData` o
`responseType: 'blob'|'arraybuffer'` a `VITE_API_UPLOAD_URL`. Excepción: el link
firmado al PDF que comparte el bot se abre en el navegador vía
`erp.soldigem.com.pe` (≈ 1,3 MB, GET simple).

### Webhook de Telegram

Se registra contra **Cloud Run directo**, nunca contra erp.soldigem.com.pe:

```
python manage.py telegram_set_webhook \
    --url https://erp-backend-25656632090.southamerica-west1.run.app
```

El comando rechaza cualquier host que no sea `*.run.app` (salvo `--forzar`).

### Prueba manual post-deploy
1. iPhone real: login → cerrar la PWA → reabrir → sigue dentro.
2. DevTools en erp.soldigem.com.pe: `refresh_token` con `Path=/api/; Secure;
   HttpOnly; SameSite=Lax`, sin `Domain`. Las llamadas JSON salen a
   `erp.soldigem.com.pe/api/…`.
3. Subir un comprobante de ~9 MB y exportar el Excel de ventas: salen a
   `…run.app` y el Excel conserva su nombre.
4. `curl -sI https://erp.soldigem.com.pe/api/core/tipo-cambio/` → responde
   Django (no el `index.html` del SPA).
5. Ver que ninguna respuesta de `/api/` trae `x-vercel-cache: HIT`.

**Efecto en sesiones activas:** la cookie vieja vivía en el host `*.run.app`;
todos los usuarios hacen **un** login extra tras este deploy.

## 11. Pre-deploy de `feat/agente-canales` (incluye `fix/review-movil`)

**Supuesto:** prod = `main` (cuadra con la última migración de `ai_assistant` en
prod, `0005`, que es la de `main`). Confirmarlo antes con el plan:
`gcloud run jobs update erp-migrate ... --args manage.py,migrate,--plan` → execute.

### Migraciones que corren en prod

Plan verificado contra un clon **de solo lectura** del esquema y de
`django_migrations` de prod (`pg_dump`, cargado en una BD local aparte):

| Migración | Qué hace | Reversible |
|---|---|---|
| `authentication.0003_simplificar_roles` | **Datos**: `readonly`→`solo_lectura`; `comercial`/`produccion`/`almacen`/`contador`/`personalizado`→`operador`; `admin` igual. Salvaguardas: superusuarios e `is_staff` → `admin`; toda empresa sin admin activo asciende a su usuario activo más antiguo. Default nuevo: `operador` | Sí, **con pérdida** (vuelve como `readonly`/`comercial`; los ascendidos quedan `admin`) |
| `canales.0001_initial` | 3 tablas nuevas: `VinculacionTelegram`, `UpdateProcesado`, `BorradorAgente` | Sí (`migrate canales zero`) |
| `empresas.0009_uuid_default_en_bd` | `DEFAULT gen_random_uuid()` en `empresas_empresa.uuid`. En prod ya existe: no cambia nada | No-op atrás |
| `compras.0026_proveedor_telefono_como_el_modelo` | **Bug de prod**: `compras_proveedor.telefono` es `varchar(9) NOT NULL`; el modelo dice `max_length=15, null=True`. Hoy crear un proveedor sin teléfono da 500. Ensancha y quita NOT NULL, sin tocar filas | No-op atrás |

`compras.0002_squashed_0009_reparacion_bd_limpia` **no corre en prod**: tiene
`replaces` de 0002…0009, que prod ya tiene aplicadas, así que Django la da por
aplicada. Solo se usa al crear una BD desde cero. Las migraciones 0002, 0003,
0007 y 0009 están **idénticas a `main`** (ninguna migración aplicada en prod se
edita). Esquema BD limpia vs. prod tras migrar: idéntico (columnas, tipos,
nulabilidad, defaults, restricciones e índices).

**Antes de migrar:** `SELECT rol, is_superuser, count(*) FROM authentication_customuser GROUP BY 1,2;`
**Después:** `SELECT e.id, e.nombre FROM empresas_empresa e WHERE NOT EXISTS (SELECT 1 FROM authentication_customuser u WHERE u.empresa_id=e.id AND u.rol='admin' AND u.is_active) AND EXISTS (SELECT 1 FROM authentication_customuser u WHERE u.empresa_id=e.id);` → 0 filas.

Derivas de prod que esta rama **no** corrige (necesitan revisar datos antes):
- `compras_compra` sin `unique (empresa_id, numero)` (0008 figura aplicada pero no corrió): se admiten números de compra duplicados.
- `compras_comprarecurrente` conserva columnas `NOT NULL` que el modelo ya no tiene (tabla sin uso, 0 filas).

`feat/registro-piloto` **no está en prod ni en `main`** (prod no tiene ninguna
migración de la app `registro`). No se mezcla en esta rama.

### Cloud Run — variables y secretos

| Tipo | Nombre | Valor |
|---|---|---|
| Secreto **nuevo** | `TG_BOT_TOKEN` | token de @BotFather → secreto `TG_BOT_TOKEN` |
| Secreto **nuevo** | `TG_WEBHOOK_SECRET` | `openssl rand -hex 32` → secreto `TG_WEBHOOK_SECRET` |
| Variable **nueva** | `TG_BOT_USERNAME` | usuario del bot, sin `@` |
| Variable **cambia** | `DJANGO_ALLOWED_HOSTS` | `erp-backend-25656632090.southamerica-west1.run.app,erp.soldigem.com.pe` |
| Variable opcional | `API_BASE_URL` | default `https://erp.soldigem.com.pe` (links al PDF) |
| Variable opcional | `CANALES_LIMITE_MENSAJES_EMPRESA_DIA` / `CANALES_LIMITE_TOKENS_EMPRESA_DIA` | default `1000` / `300000` |
| **Borrar** si existe | `REFRESH_COOKIE_DOMAIN` | ya no se usa |

```bash
printf '%s' '<token de BotFather>' | gcloud secrets create TG_BOT_TOKEN --data-file=-
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create TG_WEBHOOK_SECRET --data-file=-
for S in TG_BOT_TOKEN TG_WEBHOOK_SECRET; do
  gcloud secrets add-iam-policy-binding $S \
    --member="serviceAccount:25656632090-compute@developer.gserviceaccount.com" \
    --role=roles/secretmanager.secretAccessor
done
export SECRETS="$SECRETS,TG_BOT_TOKEN=TG_BOT_TOKEN:latest,TG_WEBHOOK_SECRET=TG_WEBHOOK_SECRET:latest"
```

### Vercel — ver §10
`VITE_API_URL` = **vacío**; `VITE_API_UPLOAD_URL` =
`https://erp-backend-25656632090.southamerica-west1.run.app`. Redeploy del frontend.

### Registrar el webhook (Cloud Run Job, una vez; después de desplegar el backend)

```bash
gcloud run jobs create erp-telegram-webhook \
  --image "$IMAGE@$DIGEST" --region $REGION \
  --command python \
  --args manage.py,telegram_set_webhook,--url,https://erp-backend-25656632090.southamerica-west1.run.app \
  --env-vars-file /tmp/erp-env-vars.yaml --set-secrets "$SECRETS" \
  --max-retries 0 --task-timeout 2m

gcloud run jobs execute erp-telegram-webhook --region $REGION --wait
```

Contra la URL **directa de Cloud Run** (el comando rechaza cualquier host que no
sea `*.run.app`). Comprobar: `curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`
→ `url` termina en `/api/canales/telegram/` y `last_error_message` vacío.
