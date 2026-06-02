# Scripts de Migración Multi-Tenant Enterprise

## Orden de Ejecución (CRÍTICO)

```
01_corregir_fk_tipos.sql       → Corrige tipos de FK inconsistentes (integer → bigint)
02_agregar_empresa_id.sql      → Agrega columna empresa_id a 20 tablas hijas
03_poblar_empresa_id.sql       → Pobla empresa_id con JOINs + NOT NULL + FKs
04_crear_indices.sql           → Crea 56 índices estratégicos (CONCURRENTLY)
05_activar_rls.sql             → Activa RLS en 55 tablas + 45 políticas
06_soft_delete.sql             → Soft delete en 14 tablas + funciones helper
07_crear_enums.sql             → 16 CHECK constraints para estados críticos
08_auditoria.sql               → Tabla audit_log + triggers en 33 tablas
```

**Estado:** ✅ Todos los scripts ejecutados exitosamente en Supabase (2026-02-24)

## Cómo Ejecutar

### Opción 1: Paso a Paso (Recomendado)

```bash
# Conectar a Supabase
PGPASSWORD='tu_password' psql -h db.xxx.supabase.co -U postgres -d postgres

# Ejecutar cada script en orden
\i migrations_sql/01_corregir_fk_tipos.sql
# Verificar resultado antes de continuar
\i migrations_sql/02_agregar_empresa_id.sql
# ... y así sucesivamente
```

### Opción 2: Script Automatizado

```bash
cd /Users/renatocardenas/Desktop/ERP/ERP_system

# Ejecutar todos los scripts
for script in migrations_sql/0*.sql; do
    echo "Ejecutando: $script"
    PGPASSWORD='YOUR_PASSWORD_HERE' psql \
        -h db.YOUR_PROJECT_REF.supabase.co \
        -U postgres -d postgres \
        -f "$script"
    echo "---"
done
```

## Verificación Post-Migración

```sql
-- 1. Verificar tablas con RLS
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;

-- 2. Verificar políticas RLS
SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public';

-- 3. Verificar que todas las tablas tienen empresa_id
SELECT table_name FROM information_schema.tables t
WHERE table_schema = 'public' 
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns c 
    WHERE c.table_name = t.table_name AND c.column_name = 'empresa_id'
)
AND table_name NOT LIKE 'django_%'
AND table_name NOT LIKE 'auth_%';

-- 4. Verificar soft delete
SELECT table_name 
FROM information_schema.columns 
WHERE column_name = 'deleted_at' AND table_schema = 'public';
```

## Configuración Django

### 1. Middleware ✅ COMPLETADO

```python
# settings.py - YA CONFIGURADO
MIDDLEWARE = [
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.tenant.TenantMiddleware',  # ✅ Activo
    # ...
]

# DATABASES - YA CONFIGURADO
'ATOMIC_REQUESTS': True  # ✅ Necesario para SET/RESET transaccional
```

### 2. Crear Migraciones Django (PENDIENTE)

```bash
cd backend
python manage.py makemigrations
python manage.py migrate --fake  # Solo marca como aplicadas (cambios ya hechos en SQL)
```

### 3. Actualizar Modelos (PENDIENTE - Opcional pero recomendado)

Los modelos pueden heredar de los nuevos modelos base:

```python
from apps.core.models.base import SoftDeleteModel

class Cliente(SoftDeleteModel):
    # ... campos existentes ...
    pass
```

## Rollback

En caso de problemas, los scripts son reversibles:

```sql
-- Desactivar RLS
ALTER TABLE nombre_tabla DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS policy_name ON nombre_tabla;

-- Eliminar columna empresa_id
ALTER TABLE nombre_tabla DROP COLUMN IF EXISTS empresa_id;

-- Eliminar soft delete
ALTER TABLE nombre_tabla DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE nombre_tabla DROP COLUMN IF EXISTS deleted_by;
```

## Notas Importantes

1. **Backup**: Siempre hacer backup antes de ejecutar
2. **Staging**: Probar en staging primero
3. **Monitoreo**: Monitorear performance después de activar RLS
4. **Downtime**: Los scripts están diseñados para mínimo downtime
