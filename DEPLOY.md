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

**Alternativa recomendada (A): correr la migración DESDE LOCAL.**
El comando `migrar_media_a_gcs` ya lee de `MEDIA_ROOT` local y escribe al storage por
defecto (GCS) + actualiza la BD. Corriéndolo en la máquina de desarrollo (donde viven
los archivos) apuntando a GCS y a la BD de producción, migra sin meter datos de cliente
en la imagen. Es una migración de datos de una sola vez, no algo que la imagen deba cargar.

```bash
# En local, con los archivos en backend/media/:
gcloud auth application-default login          # credenciales ADC (una vez)
cd backend && source ../venv/bin/activate
export GS_BUCKET_NAME=erp-system-468516-media GS_PROJECT_ID=erp-system-468516
# (la BD apunta a producción en settings; confirmar antes de ejecutar)
python manage.py migrar_media_a_gcs --dry-run  # revisar qué subiría
python manage.py migrar_media_a_gcs            # subir + actualizar BD (idempotente)
```

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

## 4. Inventario de media local a migrar (hoy)

29 archivos, 3.1 MB. Por carpeta/tipo (sin abrir contenido):

| Carpeta | Archivos | Tipo | Relevancia |
|---|---|---|---|
| `importaciones/` | 15 | xlsx | Históricos de importación (bajo valor) |
| `ventas/comprobantes/` + `comprobantes/` | 7 | pdf | Comprobantes de pago (persistentes) |
| `logos/` | 2 | png/jpg | **Logos de empresa (usados en PDFs)** |
| `firmas/` | 2 | png | **Firmas de empresa (usadas en PDFs)** |

Los críticos son **logos y firmas** (salen en cotizaciones/OC/guías). `migrar_media_a_gcs`
migra todos los campos de archivo; los xlsx de importación pueden migrarse o ignorarse.

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
