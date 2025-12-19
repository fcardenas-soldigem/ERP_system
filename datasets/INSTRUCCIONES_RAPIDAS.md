# 🚀 Instrucciones Rápidas - Subir Datasets

## 📋 Pasos Simples

### 1. Sube tus archivos aquí:

```
datasets/
  ├── clientes/      ← Datos de clientes aquí
  ├── productos/     ← Catálogo de productos aquí
  ├── ventas/        ← Historial de ventas aquí
  ├── transacciones/ ← Transacciones/canastas aquí
  ├── inventario/    ← Movimientos de stock aquí
  └── raw/           ← Si no sabes dónde, ponlos aquí
```

### 2. Formatos aceptados:
- ✅ CSV (recomendado)
- ✅ Excel (.xlsx, .xls)
- ✅ JSON

### 3. Después de subir, ejecuta:

```bash
# Ver qué datos tienes
python3 scripts/analyze_datasets.py

# Entrenar modelos (cuando los datos estén listos)
python3 scripts/train_all_models.py
```

---

## 📊 ¿Qué datos necesitas?

### Para Segmentación de Clientes (RFM):
```
clientes/ o ventas/
- cliente_id
- fecha_compra
- monto
```
Mínimo: 50 clientes

### Para Predicción de Churn:
```
clientes/
- cliente_id
- fecha_ultima_compra
- total_compras
- valor_total
```
Mínimo: 100 clientes

### Para Recomendaciones:
```
transacciones/
- transaccion_id (o venta_id)
- producto_id
```
Mínimo: 100 transacciones

### Para Predicción de Demanda:
```
ventas/
- producto_id
- fecha (diaria)
- cantidad
```
Mínimo: 30 días

---

## 🔍 Verificación Rápida

Una vez subidos tus archivos:

```bash
# Ir a la carpeta del proyecto
cd /Users/renatocardenas/Desktop/ERP/ERP_system

# Analizar datasets
python3 scripts/analyze_datasets.py
```

El script te dirá:
- ✅ Qué modelos puedes entrenar
- ❌ Qué datos faltan
- 📊 Estadísticas de tus datos

---

## 💡 Ejemplos de Nombres

**Buenos nombres de archivos:**
- `clientes_2024.csv`
- `ventas_historico.xlsx`
- `transacciones_completas.csv`
- `productos_catalogo.csv`

**Evitar:**
- `datos.csv` (muy genérico)
- `archivo final final v2.xlsx` (confuso)

---

## ⚠️ Recordatorios

1. **NO subir** datos sensibles sin anonimizar
2. Los archivos **NO se suben a Git** (están en .gitignore)
3. Si tienes dudas, ponlos en `raw/` y los reviso

---

## 🆘 ¿Problemas?

Si tienes errores o dudas, avísame y te ayudo a:
- Limpiar los datos
- Convertir formatos
- Mapear columnas
- Resolver errores

---

**Listo para revisar tus datos cuando los subas!** 📊

