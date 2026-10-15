# Despliegue — release conjunto (media persistente en GCS + landing)

Secuencia de pre-deploy y deploy para el merge a `main` de:
- **fix/media-gcs** — archivos subidos persistentes en Google Cloud Storage (resuelve R1
  de FASE2_SPEC: hoy se pierden en cada deploy).
- **feat/landing** — landing pública, captura de leads e IP real tras proxies.

> **Estado del merge:** `main` ya contiene ambos (commit `bf90f37` Merge + `FASE2_SPEC.md`).
> **NO se ha hecho push ni deploy.**

## 0. Verificación local (hecha)

- Suite completa: **97/97** tests de `apps` en verde (el único fallo del runner es
  `backend/test_import.py`, script legado del commit inicial `9b05dbc`, ajeno a este
  release — importa un símbolo inexistente).
- `python manage.py makemigrations --check --dry-run` → **No changes detected**.
- Build ERP frontend: **OK**. Build landing: **OK**.
- `django-storages[google]` importa correctamente en el venv.

## 1. Variables de entorno (añadir a `/tmp/erp-env-vars.yaml`)

```yaml
GS_BUCKET_NAME: erp-system-468516-media
GS_PROJECT_ID: erp-system-468516
```

Con `GS_BUCKET_NAME` definido, el ERP usa GCS automáticamente (URLs firmadas v4,
expiración 15 min); sin esa variable sigue en disco local (dev). La firma de URLs no
usa archivo de llave: la Service Account de Cloud Run firma vía IAM `signBlob` (tiene
`roles/iam.serviceAccountTokenCreator` sobre sí misma) y `objectAdmin` sobre el bucket.

## 2. ⚠️ Los archivos locales NO entran en la imagen Docker

`.gcloudignore:18` excluye `backend/media/`, así que `gcloud builds submit` no lo sube
al contexto de Cloud Build y el `COPY backend/ /app` del Dockerfile no lo incluye:
**`/app/media` queda vacío en la imagen.** (`.dockerignore` no excluye media, pero eso
solo aplicaría a un `docker build` local; la ruta de Cloud Build gana.)

Consecuencia: **no se puede** correr `migrar_media_a_gcs` como Cloud Run Job esperando
que `/app/media` tenga las firmas/logos locales — no estarán ahí.

**Alternativa recomendada (A): correr la migración DESDE LOCAL, apuntando a la BD de prod.**
El comando `migrar_media_a_gcs` está **guiado por la BD**: recorre los `FileField` de la
BD destino (`model.objects`, no el directorio), busca cada archivo referenciado en
`MEDIA_ROOT` local y sube SOLO los que están referenciados. Los archivos locales sin
registro en la BD destino (pruebas de dev) **no se suben**. Es una migración de datos de
una sola vez; no algo que la imagen deba cargar.

```bash
cd backend && source ../venv/bin/activate
gcloud auth application-default login          # ADC del usuario (una vez; necesario para SUBIR)

# DRY-RUN contra PROD (solo lee BD + revisa disco local; no sube nada):
DOTENV_FILE=.env.production \
GS_BUCKET_NAME=erp-system-468516-media GS_PROJECT_ID=erp-system-468516 \
  python manage.py migrar_media_a_gcs --dry-run

# Real (sube a GCS + actualiza la BD de prod; idempotente, re-ejecutable):
DOTENV_FILE=.env.production \
GS_BUCKET_NAME=erp-system-468516-media GS_PROJECT_ID=erp-system-468516 \
  python manage.py migrar_media_a_gcs
```

`DOTENV_FILE=.env.production` fuerza la BD de prod desde local (ver `settings.py:19-28`;
por defecto NO se carga). El `--dry-run` no toca GCS ni la BD (no requiere ADC); el real sí.

**Resultado del dry-run contra PROD (ejecutado):**
`Migrados: 18 | Ya migrados: 0 | Faltantes en disco: 1`
- 18 a subir: `Empresa#1` logo + 2 firmas (los críticos de los PDFs) + 15 `ImportacionExcel` xlsx.
- 1 faltante en local: `ImportacionExcel#20` (referenciado en prod, perdido en un deploy
  previo con disco efímero). Tras migrar, `auditar_archivos` lo listará.
- Los 7 PDF de comprobantes que hay en `backend/media/` local **no aparecen**: no tienen
  registro en la BD de prod → el comando los ignora (comportamiento guiado por BD, correcto).

**Alternativa (B): Cloud Run Job con media en la imagen.** Comentar `backend/media/` en
`.gcloudignore` solo para un build, desplegar el Job, ejecutarlo y volver a ignorar.
Desventaja: hornea ~3 MB de archivos de cliente en una capa de imagen (queda en el
historial del registry) y acopla una migración de datos a un deploy. No recomendada.

## 3. Orden de deploy del backend

El ERP degrada con gracia si un archivo falta (los serializers devuelven URL nula →
la UI muestra "Archivo no disponible"; los PDF omiten logo/firma), así que el orden
seguro es activar GCS primero y migrar después:

1. **Desplegar la imagen nueva con las env vars de §1.** El ERP pasa a usar GCS. Las
   filas existentes aún apuntan a rutas viejas (`logos/x.png`) → logo/firma temporalmente
   ausentes hasta el paso 3.
2. **Aplicar migraciones** (`python manage.py migrate`, o Cloud Run Job de migrate). Son
   `AlterField` (cambian `upload_to`/validators); no alteran el esquema, no tocan datos.
3. **Migrar la media** con `migrar_media_a_gcs` (Alternativa A, §2): sube los archivos a
   GCS con rutas `empresa_<id>/<tipo>/<uuid>.<ext>` y actualiza la BD. Tras esto, logos y
   firmas resuelven desde GCS.
4. **Auditar**: `python manage.py auditar_archivos` lista los registros cuyo archivo no
   existe en el storage (los perdidos en deploys anteriores, cuando media era efímera).
   Solo reporta; decidir caso por caso (re-subir o limpiar la referencia).

## 4. Inventario de media local vs. lo que se migra

`backend/media/` local: **29 archivos, 3.1 MB** (15 xlsx, 7 pdf, 3 png, 3 jpeg, 1 jpg).
Pero la migración es **guiada por la BD**, no por el directorio: contra la BD de prod,
el dry-run reporta **19 registros con archivo** → **18 presentes en local** (se subirían) +
**1 faltante** (`ImportacionExcel#20`). Los **7 PDF de comprobantes** locales son de dev
(sin registro en prod) y **no se migran**.

| Qué | En local | En BD prod | Se migra |
|---|---|---|---|
| `Empresa#1` logo + 2 firmas | sí | sí | **sí (críticos de PDFs)** |
| 15 `ImportacionExcel` xlsx | sí | sí | sí (históricos) |
| `ImportacionExcel#20` xlsx | **no** | sí | no se puede (falta en disco) |
| 7 PDF de comprobantes | sí | **no** | **no (dev-only, correcto)** |

## 5. Landing

Deploy de la landing: ver `landing/DEPLOY.md` (proyecto Vercel aparte; rewrite `/api/*`
→ Cloud Run, resto → ERP en Vercel). Sin cambios de backend adicionales para la landing
en este release más allá de lo ya mergeado.

## 6. Rollback

- Backend: redeploy de la imagen anterior y **quitar** `GS_BUCKET_NAME`/`GS_PROJECT_ID`
  → vuelve a disco local. Las migraciones `AlterField` no necesitan revertirse (no cambian
  el esquema); si se desea, `migrate <app> <migración_anterior>`.
- Las filas ya migradas apuntarán a GCS; si se revierte a disco local quedarían sin
  archivo (mostrarán "Archivo no disponible"). Por eso conviene no revertir tras el paso 3
  salvo necesidad real.
