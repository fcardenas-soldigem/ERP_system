# 🚀 CREAR TABLAS DE PRODUCCIÓN EN POSTGRESQL

## ✅ ESTADO ACTUAL

Se han actualizado y creado **todos los modelos** de Django para producción:

### Modelos Actualizados:
1. ✅ `Producto` - Agregado campo `tipo_producto` (RAW, SEMIFINISHED, FINISHED)

### Modelos Nuevos Creados:
2. ✅ `RecetaProducto` (ProductionRecipe)
3. ✅ `RecetaDetalle` (ProductionRecipeItem)
4. ✅ `OrdenProduccion` (ProductionOrder)
5. ✅ `ConsumoReal` (ProductionConsumption)
6. ✅ `ProductionOutput` (Producción parcial/lotes) - **NUEVO**
7. ✅ `ProductionWaste` (Mermas detalladas) - **NUEVO**
8. ✅ `ProductionCost` (Snapshot de costos) - **NUEVO**

---

## 📋 PASO A PASO PARA CREAR LAS TABLAS

### Opción 1: Usando Django Migrations (RECOMENDADO)

```bash
# 1. Ir al directorio del backend
cd /Users/renatocardenas/.cursor/worktrees/ERP_system/hps/backend

# 2. Crear las migraciones
python3 manage.py makemigrations inventario
python3 manage.py makemigrations produccion

# Deberías ver algo como:
# Migrations for 'inventario':
#   inventario/migrations/0008_producto_tipo_producto.py
#     - Add field tipo_producto to producto
#
# Migrations for 'produccion':
#   produccion/migrations/0001_initial.py
#     - Create model RecetaProducto
#     - Create model RecetaDetalle
#     - Create model OrdenProduccion
#     - Create model ConsumoReal
#     - Create model ProductionOutput
#     - Create model ProductionWaste
#     - Create model ProductionCost

# 3. Ver el SQL que se ejecutará (opcional, para verificar)
python3 manage.py sqlmigrate produccion 0001

# 4. Aplicar las migraciones a PostgreSQL
python3 manage.py migrate

# Deberías ver:
# Running migrations:
#   Applying inventario.0008_producto_tipo_producto... OK
#   Applying produccion.0001_initial... OK
```

### Opción 2: SQL Directo (Solo si quieres ver el SQL)

Si quieres ver el SQL que Django generará antes de ejecutarlo:

```bash
python3 manage.py sqlmigrate produccion 0001 > produccion_schema.sql
```

Esto creará un archivo `produccion_schema.sql` con todas las sentencias CREATE TABLE.

---

## 🔍 VERIFICAR QUE LAS TABLAS SE CREARON

```bash
# Opción 1: Desde Django shell
python3 manage.py dbshell

# Dentro de psql:
\dt produccion_*

# Deberías ver:
# produccion_recetaproducto
# produccion_recetadetalle
# produccion_ordenproduccion
# produccion_consumoreal
# produccion_productionoutput
# produccion_productionwaste
# produccion_productioncost

# Salir
\q
```

```bash
# Opción 2: Verificar desde Python
python3 manage.py shell

# En el shell:
from apps.produccion.models import *
from apps.inventario.models import Producto

# Ver si las tablas existen
print(RecetaProducto.objects.count())  # Debería devolver 0
print(OrdenProduccion.objects.count())  # Debería devolver 0
print(ProductionCost.objects.count())   # Debería devolver 0

# Verificar campo nuevo en Producto
print(Producto.TIPO_PRODUCTO_CHOICES)  # Debería mostrar RAW, SEMIFINISHED, FINISHED

exit()
```

---

## 📊 TABLAS QUE SE CREARÁN

### En el esquema `public`:

| # | Tabla | Registros esperados |
|---|-------|---------------------|
| 1 | `inventario_producto` | ACTUALIZADA (campo `tipo_producto`) |
| 2 | `produccion_recetaproducto` | Recetas de producción |
| 3 | `produccion_recetadetalle` | Insumos por receta |
| 4 | `produccion_ordenproduccion` | Órdenes de trabajo |
| 5 | `produccion_consumoreal` | Consumos reales |
| 6 | `produccion_productionoutput` | Lotes/cierres parciales |
| 7 | `produccion_productionwaste` | Mermas detalladas |
| 8 | `produccion_productioncost` | Snapshot de costos |

**Total: 7 tablas nuevas + 1 tabla actualizada = 8 tablas afectadas**

---

## ⚙️ CONFIGURACIÓN DE INDICES

Django creará automáticamente estos índices para optimizar consultas:

```sql
-- Recetas
CREATE INDEX idx_receta_empresa ON produccion_recetaproducto(empresa_id);
CREATE INDEX idx_receta_producto ON produccion_recetaproducto(producto_terminado_id);
CREATE INDEX idx_receta_active ON produccion_recetaproducto(is_active);

-- Órdenes
CREATE INDEX idx_orden_empresa ON produccion_ordenproduccion(empresa_id);
CREATE INDEX idx_orden_estado ON produccion_ordenproduccion(estado);
CREATE INDEX idx_orden_fecha_prog ON produccion_ordenproduccion(fecha_programada);
CREATE INDEX idx_orden_numero ON produccion_ordenproduccion(numero);

-- Consumos
CREATE INDEX idx_consumo_orden ON produccion_consumoreal(orden_produccion_id);
CREATE INDEX idx_consumo_insumo ON produccion_consumoreal(insumo_id);

-- Y muchos más...
```

---

## 🧪 DATOS DE PRUEBA (Opcional)

Después de crear las tablas, puedes probar creando datos de ejemplo:

```bash
python3 manage.py shell
```

```python
from apps.produccion.models import *
from apps.inventario.models import Producto, Almacen
from apps.empresas.models import Empresa

# 1. Obtener empresa (asume que ya existe)
empresa = Empresa.objects.first()

# 2. Crear productos de prueba
# Insumo 1
harina = Producto.objects.create(
    empresa=empresa,
    sku='INS-001',
    nombre='Harina',
    tipo_producto='RAW',
    unidad_medida='kilo',
    precio_compra=2.50
)

# Insumo 2
azucar = Producto.objects.create(
    empresa=empresa,
    sku='INS-002',
    nombre='Azúcar',
    tipo_producto='RAW',
    unidad_medida='kilo',
    precio_compra=3.00
)

# Producto Terminado
pan = Producto.objects.create(
    empresa=empresa,
    sku='PROD-001',
    nombre='Pan',
    tipo_producto='FINISHED',
    unidad_medida='unidad',
    precio_venta=1.50
)

# 3. Crear receta
receta = RecetaProducto.objects.create(
    empresa=empresa,
    producto_terminado=pan,
    nombre='Receta Pan Tradicional',
    cantidad_producida=10,
    tiempo_estimado=30,
    costo_mano_obra=5.00,
    costo_indirecto=2.00
)

# 4. Agregar insumos a la receta
RecetaDetalle.objects.create(
    receta=receta,
    insumo=harina,
    cantidad=1.0,
    unidad_medida='kilo',
    costo_unitario=2.50
)

RecetaDetalle.objects.create(
    receta=receta,
    insumo=azucar,
    cantidad=0.5,
    unidad_medida='kilo',
    costo_unitario=3.00
)

print("✅ Datos de prueba creados!")
print(f"Receta: {receta.nombre}")
print(f"Insumos: {receta.detalles.count()}")
print(f"Costo teórico: {receta.calcular_costo_teorico()}")
```

---

## 🔧 TROUBLESHOOTING

### Error: "No module named apps.produccion"

```bash
# Verificar que la app esté en INSTALLED_APPS
grep produccion backend/config/settings.py

# Debería aparecer:
# 'apps.produccion',
```

### Error: "relation produccion_... does not exist"

```bash
# Ejecutar migraciones
python3 manage.py migrate produccion
```

### Error: "column tipo_producto does not exist"

```bash
# Migrar inventario primero
python3 manage.py migrate inventario
```

### Ver todas las migraciones pendientes

```bash
python3 manage.py showmigrations produccion
```

### Revertir migraciones (si es necesario)

```bash
# Revertir última migración de producción
python3 manage.py migrate produccion zero

# Revertir y volver a aplicar
python3 manage.py migrate produccion
```

---

## ✅ CHECKLIST FINAL

Antes de decir "todo listo", verifica:

- [ ] Migraciones de `inventario` aplicadas (campo `tipo_producto`)
- [ ] Migraciones de `produccion` aplicadas (7 tablas nuevas)
- [ ] Servidor Django inicia sin errores
- [ ] Puedes acceder al admin de Django → Producción
- [ ] Las tablas aparecen en `\dt produccion_*`
- [ ] Los modelos se pueden importar sin error

---

## 🎯 PRÓXIMOS PASOS

Una vez creadas las tablas:

1. ✅ **Iniciar el servidor backend**
   ```bash
   python3 manage.py runserver 0.0.0.0:8080
   ```

2. ✅ **Iniciar el frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. ✅ **Acceder al módulo**
   - Login en el sistema
   - Menú lateral → "Producción" (ícono de fábrica)
   - Crear primera receta
   - Crear primera orden
   - Ejecutar producción

---

## 📞 SOPORTE

Si algo no funciona:

1. Ver logs de Django:
   ```bash
   tail -f backend/logs/django.log
   ```

2. Ver migraciones aplicadas:
   ```bash
   python3 manage.py showmigrations
   ```

3. Ver SQL generado:
   ```bash
   python3 manage.py sqlmigrate produccion 0001
   ```

---

## 🎉 RESULTADO ESPERADO

Después de ejecutar las migraciones, deberías poder:

```bash
python3 manage.py dbshell
```

```sql
-- Ver todas las tablas de producción
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE 'produccion_%';

-- Resultado esperado:
 table_name                        
-----------------------------------
 produccion_recetaproducto
 produccion_recetadetalle
 produccion_ordenproduccion
 produccion_consumoreal
 produccion_productionoutput
 produccion_productionwaste
 produccion_productioncost
(7 rows)
```

---

**¡Todo listo para producción! 🚀**

**Ejecuta:**
```bash
cd backend
python3 manage.py makemigrations
python3 manage.py migrate
```

**Y las tablas se crearán automáticamente en PostgreSQL.**
