# Backend ERP — entorno local vs producción

## ⚠️ Regla de oro
La BD de **producción es Supabase**. El desarrollo local **NUNCA** debe apuntar
ahí. Por eso las credenciales se separan en archivos distintos (todos en
`.gitignore`, nunca se commitean):

| Archivo | Uso | ¿Se carga por defecto? |
|---------|-----|------------------------|
| `backend/.env.local` | Desarrollo local (Postgres en Docker, `DB_HOST=localhost`) | **Sí**, si existe |
| `backend/.env.production` | Credenciales de Supabase (prod) | **No** |
| `backend/.env` | (obsoleto) fallback si no hay `.env.local` | Solo si no existe `.env.local` |

`config/settings.py` elige el archivo así:
1. Si `DOTENV_FILE=<archivo>` está seteado → usa ese.
2. Si existe `.env.local` → lo usa.
3. Si no → `.env`.

## Correr en local (sin tocar producción)

1. Levantar Postgres local (requiere Docker Desktop corriendo):
   ```bash
   docker compose up -d db
   ```
   Crea una BD `erp` (user `postgres` / pass `postgres`) en **`localhost:5433`**
   (el `5432` suele estar ocupado por un Postgres nativo). La imagen es
   `postgres:17`, igual major que prod. `backend/.env.local` ya apunta a `5433`.

2. **Clonar el esquema de prod a local** (recomendado). Un `migrate` desde cero
   NO funciona hoy por una deuda en las migraciones de `compras` (R4: `0002` y
   `0004` chocan en `created_at`). En su lugar se clona el esquema real:
   ```bash
   ./scripts/clone_prod_schema.sh
   ```
   El script: levanta la BD local, hace `pg_dump` SOLO LECTURA del schema
   `public` + la tabla `django_migrations` de prod, los carga en local, y
   verifica que `migrate` diga **"No migrations to apply"**. No copia datos de
   clientes. Los dumps quedan en `/tmp` (nunca se commitean).

3. Correr, desde `backend/`:
   ```bash
   source ../venv/bin/activate
   python manage.py runserver   # usa .env.local → localhost:5433
   python manage.py createsuperuser   # (o crear vía ORM; USERNAME_FIELD=email)
   ```

## Correr contra producción (solo cuando sea estrictamente necesario)

```bash
DOTENV_FILE=.env.production python manage.py <comando>
```
Nunca corras `migrate` contra prod sin saber exactamente qué hace. Toda migración
nueva con columnas `NOT NULL` debe traer `DEFAULT` a nivel de BD (ver
`ventas/0019_set_db_defaults_columnas_nuevas.py`) para no romper el código viejo
que aún corre en Cloud Run.

## Tests

```bash
# SQLite en memoria (rápido, no toca ninguna BD real):
python manage.py test apps.cotizaciones.tests.test_conversion_dual --settings=config.settings_test

# Contra el Postgres local (fidelidad de engine, crea test_erp en localhost:5433):
python manage.py test apps.cotizaciones.tests.test_conversion_dual --settings=config.settings_test_pg --noinput
```
Ambos settings usan una URLconf vacía (evitan importar el stack de ML ausente en
dev) y deshabilitan migraciones (syncdb desde los modelos) para no replayar la
deuda de `compras`; crean a mano la tabla managed=False `compras_ordencompradetalle`.
