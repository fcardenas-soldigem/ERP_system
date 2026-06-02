# Auditoría de Integridad de Datos — ERP System
**Fecha:** 2026-05-31  
**Empresa:** Soluciones Digitales Empresariales (ID=1, RUC=20603231717)

---

## Resumen Ejecutivo

El dashboard mostraba datos financieros incorrectos. La investigación encontró
**3 problemas reales** y **descartó 2 bugs que no existen** en estos datos.

| Estado | Descripción |
|--------|-------------|
| ✅ Correcto | Conversión USD→PEN ya implementada en todos los endpoints |
| ✅ Correcto | Precios de compra son reales (min=$5.32, max=$4,269.98, prom=$880.66) |
| ✅ Correcto | Integridad detalles de venta — totales cuadran con detalles |
| ❌ Corregido | Labels "Por Cobrar"/"Por Pagar" usaban IGV en vez de cuentas pendientes |
| ❌ Corregido | Alerta de compras en borrador ausente → utilidad aparecía inflada |
| ⚠️ Acción pendiente | 30 compras en borrador (S/383,408) no están aprobadas |

---

## Lo que hay en la base de datos

### Ventas
| Métrica | Valor |
|---------|-------|
| Total ventas | 65 |
| En PEN | 31 ventas · S/ 47,817.52 |
| En USD | 34 ventas · $ 169,082.44 |
| Estado "pagado" | **65 (100%)** — todas aprobadas |
| Estado "pendiente" | 0 |
| Distribución de fechas | 57 con fecha 2026-05-31 (importación masiva) + 3 con 2026-05-30 + 5 históricas |

### Compras
| Métrica | Valor |
|---------|-------|
| Total compras | 35 |
| En USD | 35 compras · $ 157,937.69 |
| En PEN | 0 |
| Estado "pagada" | 5 compras · $ 51,973.10 |
| **Estado "borrador"** | **30 compras · $ 105,964.59 → S/ 383,408.64 en PEN** |
| Estado "pendiente" | 0 |

---

## Problemas encontrados

### PROBLEMA 1 — Labels incorrectos en stat cards (CORREGIDO)
**Tabla:** Frontend `Dashboard.jsx`  
**Síntoma:** "Por Cobrar" mostraba el IGV acumulado de ventas; "Por Pagar" mostraba el IGV acumulado de compras.  
**Causa raíz:** Las tarjetas usaban `resumen.impuestos.igv_ventas` y `resumen.impuestos.igv_compras` — datos de IGV, no de cuentas por cobrar/pagar.  
**Corrección aplicada:**
- `Dashboard.jsx` líneas 88-100: cards ahora usan `resumen.cuentas.por_cobrar` y `resumen.cuentas.por_pagar`
- Subtítulos corregidos a "Ventas pendientes de cobro" y "Compras pendientes de pago"
- Backend `DashboardResumen.get()` ahora devuelve sección `cuentas` con los valores reales

**Valor correcto:** S/ 0.00 para ambos (no hay ventas ni compras en estado "pendiente").

---

### PROBLEMA 2 — Utilidad inflada por compras en borrador (CORREGIDO — alerta añadida)
**Tabla:** `compras_compra`  
**Síntoma:** Utilidad = S/394,539 con margen 68% — imposible si hay $105,964 en compras sin pagar.  
**Causa raíz:** El endpoint `/api/dashboard/resumen/` filtra `Compra.estado='pagada'`. Las 30 compras importadas quedaron en `borrador`, invisible para el cálculo de utilidad.

**¿Cuál sería la utilidad real si se aprobaran las 30 compras?**
| Concepto | Con compras aprobadas |
|----------|-----------------------|
| Ventas netas (sin IGV) | S/ 578,230 |
| Costo real de compras (sin IGV) | S/ 508,612 |
| **Utilidad real** | **S/ 69,618** |
| **Margen real** | **~12%** (vs 68% actual) |

**Corrección aplicada:**
- Backend: `DashboardResumen` y `DashboardResumenView` ahora incluyen `cuentas.compras_borrador_count` y `cuentas.compras_borrador_total`
- Frontend: `buildAlerts()` en `Dashboard.jsx` agrega una alerta visible cuando hay compras en borrador

**Acción requerida del usuario:** Aprobar (cambiar estado a `pagada`) las 30 compras en borrador en el módulo de Compras.

---

### PROBLEMA 3 — Todas las transacciones tienen fecha de importación (INFORMATIVO)
**Tabla:** `ventas_venta`, `compras_compra`  
**Síntoma:** El gráfico del mes solo muestra actividad en días 30-31.  
**Causa raíz:** Las ventas y compras se importaron masivamente con fecha 2026-05-30 o 2026-05-31 como fecha por defecto.  
**Estado:** No es un error del sistema — es la realidad de los datos importados. Para análisis histórico correcto, re-importar con las fechas originales si están disponibles en el Excel fuente.

---

## Bugs descartados (no existen en estos datos)

| Bug reportado | Estado |
|---------------|--------|
| Precios importados en $0.01 | ❌ NO existe — precios correctos (min $5.32, max $4,269.98) |
| Ventas USD sumadas sin convertir | ❌ NO existe — `convertir_a_pen()` ya se aplica en todos los endpoints |

---

## Correcciones aplicadas

| Archivo | Línea(s) | Cambio |
|---------|----------|--------|
| `backend/apps/dashboard/views.py` | `DashboardResumen.get()` | Agrega `por_cobrar`, `por_pagar`, `compras_borrador_count`, `compras_borrador_total` al response bajo clave `cuentas` |
| `backend/apps/dashboard/views.py` | `DashboardResumenView.get()` | Ídem para el endpoint histórico |
| `frontend/src/components/Dashboard/Dashboard.jsx` | líneas 88-100 | StatCards "Por cobrar"/"Por pagar" usan `cuentas.por_cobrar`/`cuentas.por_pagar` con subtítulos correctos |
| `frontend/src/components/Dashboard/Dashboard.jsx` | `buildAlerts()` | Nueva alerta cuando `cuentas.compras_borrador_count > 0` |
| `backend/audit_datos.py` | — | Script de auditoría para diagnóstico (puede eliminarse) |

---

## Próximos pasos

1. **Acción urgente:** Revisar y aprobar las 30 compras en borrador en `/app/compras` para ver la utilidad real (~12% en lugar del 68% actual)
2. Si tienes el Excel original con fechas reales de compra, re-importar para que el gráfico histórico refleje la distribución correcta
3. Verificar tipo de cambio configurado en la empresa (`empresa.tipo_cambio_usd`) — actualmente usa el fallback de 3.8
