# 📊 Datasets para Machine Learning

Esta carpeta contiene los datasets para entrenar y validar los modelos de ML.

## 📁 Estructura de Carpetas

### 📂 `clientes/`
Datos relacionados con clientes para:
- Segmentación RFM
- Predicción de Churn
- Análisis de comportamiento

**Archivos esperados:**
- `clientes.csv` - Información básica de clientes
- `historial_compras_clientes.csv` - Historial de transacciones
- `clientes_rfm.csv` - Datos precalculados de RFM (opcional)

**Columnas sugeridas:**
```
cliente_id, nombre, email, telefono, fecha_registro, tipo_cliente, 
total_compras, valor_total, ultima_compra, primera_compra
```

---

### 📂 `productos/`
Datos de productos para:
- Recomendaciones de productos
- Análisis de categorías
- Popularidad de productos

**Archivos esperados:**
- `productos.csv` - Catálogo de productos
- `categorias.csv` - Categorías de productos
- `precios_historicos.csv` - Historial de precios

**Columnas sugeridas:**
```
producto_id, nombre, codigo, categoria, precio, costo, stock, 
proveedor, marca, descripcion
```

---

### 📂 `ventas/`
Datos de ventas para:
- Predicción de demanda
- Análisis de tendencias
- Forecasting

**Archivos esperados:**
- `ventas.csv` - Registro de ventas
- `ventas_detalle.csv` - Líneas de venta (productos)
- `ventas_diarias.csv` - Ventas agregadas por día

**Columnas sugeridas:**
```
venta_id, fecha, cliente_id, producto_id, cantidad, precio_unitario, 
total, descuento, forma_pago, vendedor
```

---

### 📂 `transacciones/`
Datos de transacciones para:
- Market Basket Analysis
- Recomendaciones
- Patrones de compra

**Archivos esperados:**
- `transacciones.csv` - Transacciones completas
- `canastas.csv` - Productos por transacción

**Columnas sugeridas:**
```
transaccion_id, fecha, cliente_id, producto_id, cantidad, 
orden_en_canasta, session_id
```

---

### 📂 `inventario/`
Datos de inventario para:
- Predicción de demanda
- Optimización de stock
- Alertas de reorden

**Archivos esperados:**
- `stock_historico.csv` - Historial de niveles de stock
- `movimientos_inventario.csv` - Entradas y salidas
- `productos_criticos.csv` - Productos con bajo stock

**Columnas sugeridas:**
```
producto_id, fecha, stock_inicial, entradas, salidas, stock_final, 
tipo_movimiento, responsable
```

---

### 📂 `raw/`
Datos sin procesar / originales
- Subir aquí los datos tal como vienen
- No modificados
- Backups

---

### 📂 `processed/`
Datos procesados y listos para ML
- Generados automáticamente por scripts
- Datos limpios y normalizados
- Features engineering aplicado

---

## 📋 Formatos Soportados

### Preferidos:
- ✅ **CSV** (UTF-8) - Más compatible
- ✅ **Excel** (.xlsx) - Fácil de editar
- ✅ **JSON** - Para datos estructurados

### También soportados:
- 📊 **Parquet** - Para datasets grandes
- 📄 **TSV** - Separado por tabs
- 🗄️ **SQLite** - Para backups de DB

---

## 🔍 Calidad de Datos Requerida

### Mínimos Recomendados:

| Modelo | Dataset | Mínimo | Óptimo |
|--------|---------|--------|--------|
| **RFM Segmentation** | Clientes con historial | 50 clientes | 500+ clientes |
| **Churn Prediction** | Clientes con compras | 100 clientes | 1000+ clientes |
| **Product Recommendations** | Transacciones | 100 transacciones | 1000+ transacciones |
| **Demand Forecasting** | Ventas diarias | 30 días | 365+ días |

### Columnas Obligatorias por Modelo:

**RFM Segmentation:**
- `cliente_id` (único)
- `fecha_compra` (datetime)
- `monto` (numérico)

**Churn Prediction:**
- `cliente_id` (único)
- `fecha_ultima_compra` (datetime)
- `total_compras` (numérico)
- `valor_total` (numérico)

**Product Recommendations:**
- `transaccion_id` (único)
- `producto_id` (único)
- Relación muchos a muchos

**Demand Forecasting:**
- `producto_id` (único)
- `fecha` (datetime, diaria)
- `cantidad_vendida` (numérico)

---

## 🧹 Limpieza de Datos

### Antes de subir, verifica:

- ✅ Sin valores nulos en columnas clave
- ✅ Fechas en formato consistente (YYYY-MM-DD)
- ✅ IDs únicos y consistentes
- ✅ Números sin símbolos de moneda ($, ,)
- ✅ Encoding UTF-8
- ✅ Sin filas duplicadas

### Scripts de limpieza disponibles:
```bash
# Ejecutar script de validación (próximamente)
python scripts/validate_datasets.py --folder clientes
```

---

## 📝 Ejemplo de Datasets

### clientes.csv
```csv
cliente_id,nombre,email,fecha_registro,tipo_cliente
1,Juan Pérez,juan@email.com,2023-01-15,Regular
2,María López,maria@email.com,2023-02-20,VIP
3,Carlos Ruiz,carlos@email.com,2023-03-10,Nuevo
```

### ventas.csv
```csv
venta_id,fecha,cliente_id,producto_id,cantidad,precio_unitario,total
1,2024-01-10,1,101,2,50.00,100.00
2,2024-01-10,1,102,1,75.00,75.00
3,2024-01-11,2,101,5,50.00,250.00
```

### transacciones.csv
```csv
transaccion_id,fecha,cliente_id,producto_id
1,2024-01-10,1,101
1,2024-01-10,1,102
2,2024-01-11,2,101
2,2024-01-11,2,103
```

---

## 🔒 Seguridad y Privacidad

### ⚠️ IMPORTANTE:

1. **NO** subir datos sensibles sin anonimizar:
   - ❌ Contraseñas
   - ❌ Números de tarjeta
   - ❌ Datos médicos
   - ❌ Documentos de identidad completos

2. **SÍ** anonimizar datos personales:
   - ✅ Usar IDs en lugar de nombres reales
   - ✅ Ofuscar emails: `usuario***@email.com`
   - ✅ Truncar teléfonos: `999-***-****`

3. **Gitignore:**
   - Esta carpeta `datasets/` está en `.gitignore`
   - Los datos NO se subirán a GitHub
   - Solo local para entrenamiento

---

## 🚀 Siguientes Pasos

### 1. Subir tus Datasets
```
datasets/
  ├── clientes/
  │   └── [TUS_ARCHIVOS_AQUI].csv
  ├── productos/
  │   └── [TUS_ARCHIVOS_AQUI].csv
  ├── ventas/
  │   └── [TUS_ARCHIVOS_AQUI].csv
  └── transacciones/
      └── [TUS_ARCHIVOS_AQUI].csv
```

### 2. Ejecutar Análisis Exploratorio
```bash
# Script para revisar calidad de datos
python scripts/analyze_datasets.py
```

### 3. Entrenar Modelos
```bash
# Entrenar todos los modelos con tus datos
python scripts/train_all_models.py
```

### 4. Validar Resultados
```bash
# Ver métricas de performance
python scripts/evaluate_models.py
```

---

## 📞 Soporte

Si tienes dudas sobre:
- ✅ Qué archivos subir
- ✅ Formato de datos
- ✅ Cómo limpiar datos
- ✅ Columnas faltantes

Avísame y te ayudo a preparar los datos correctamente.

---

## 📊 Estado Actual

```
[ ] Datasets subidos
[ ] Datos validados
[ ] Modelos entrenados
[ ] Resultados evaluados
```

---

**Fecha de creación:** Octubre 2025  
**Última actualización:** Octubre 2025

