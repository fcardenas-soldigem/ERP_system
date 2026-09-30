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
   Crea una BD `erp` (user `postgres` / pass `postgres`) en `localhost:5432`.

2. Confirmar que `backend/.env.local` existe y tiene `DB_HOST=localhost`.

3. Migrar y correr, desde `backend/`:
   ```bash
   source ../venv/bin/activate
   python manage.py migrate
   python manage.py runserver
   ```
   Esto crea las tablas en la **BD local**, no en Supabase.

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
python manage.py test apps.cotizaciones.tests.test_conversion_dual --settings=config.settings_test
```
`config/settings_test.py` usa **SQLite en memoria** (no toca ninguna BD real) y
una URLconf vacía (evita importar el stack de ML ausente en dev).
