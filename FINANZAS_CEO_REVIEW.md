# Módulo de Finanzas — CEO Review (McKinsey/Bain Framework)

> Fecha: 2026-05-30 · Modo: SELECTIVE EXPANSION · Revisado por: plan-ceo-review skill

---

## Veredicto ejecutivo

El módulo tiene buena estructura y el brief original es sólido. Los KPIs están bien seleccionados en su mayoría. Pero hay **5 bugs que distorsionan los números**, **3 KPIs críticos faltantes para el contexto peruano**, **2 KPIs que deben cortarse**, y un problema fundamental de diseño: el módulo **muestra métricas pero no provoca decisiones**. Bain diría que falta el "So What?"

---

## PARTE 1 — Bugs que rompen la matemática

### BUG-01 — CRÍTICO: `calcular_avanzados()` duplica todas las queries DB (N×2 problem)

**Archivo:** `backend/apps/finanzas/services.py:535-624`

`calcular_avanzados()` llama internamente a `calcular_cuentas_cobrar()`, `calcular_cuentas_pagar()`, `calcular_flujo_caja()` y `calcular_rentabilidad()`. La `view` en `views.py` ya llama a todos estos métodos por separado. Resultado: **9 ejecuciones de métodos** en vez de 5, con el doble de queries a Supabase remoto.

```python
# views.py:65-72 — YA llama a todos:
flujo        = svc.calcular_flujo_caja()
rentabilidad = svc.calcular_rentabilidad()
cxc          = svc.calcular_cuentas_cobrar()
cxp          = svc.calcular_cuentas_pagar()
avanzados    = svc.calcular_avanzados()  # ← esto vuelve a llamar a los 4 de arriba

# Fix: pasar los resultados ya calculados como parámetros:
avanzados = svc.calcular_avanzados(cxc=cxc, cxp=cxp, flujo=flujo, rent=rentabilidad)
```

**Impacto:** Con conexión a Supabase remoto (~50ms/query), la primera carga del módulo puede tomar 8-15 segundos en vez de 3-5s.

---

### BUG-02 — CRÍTICO: DSO explota cuando se consulta a mitad de mes

**Archivo:** `backend/apps/finanzas/services.py:353-361`

```python
# Fórmula actual:
dso = int((total_pendiente / ventas_mes * dias_periodo) if ventas_mes > 0 else 0)
```

Si hoy es el día 5 del mes y el negocio tiene S/10,000 en cuentas por cobrar históricos pero solo S/800 en ventas de los últimos 5 días: `DSO = (10000 / 800) × 30 = 375 días`. Un número absurdo que destruye la confianza del usuario.

**Fix correcto:** Usar ventas de los últimos 90 días como denominador:
```python
# Ventas rolling 90 días para denominar el DSO
ventas_90d = Venta.objects.filter(
    empresa=self.empresa,
    estado='pagado',
    fecha_emision__range=(self.hoy - timedelta(days=90), self.hoy),
).aggregate(total=Sum('total', output_field=DecimalField()))['total'] or Decimal('1')
ventas_diarias_promedio = ventas_90d / 90
dso = int(total_pendiente / ventas_diarias_promedio) if ventas_diarias_promedio > 0 else 0
```

---

### BUG-03 — ALTO: Revenue se calcula con IGV incluido → márgenes sobreestimados

**Archivo:** `backend/apps/finanzas/services.py:183-185`

`Venta.total` incluye IGV (18%). Al calcular `utilidad_bruta = ventas_total - cogs`, estamos comparando ventas con IGV vs costos sin IGV. Una venta de S/118 (neto S/100 + S/18 IGV) menos costo de S/60 da margen = S/58 (49%) cuando la realidad es S/100 - S/60 = S/40 (40%).

```python
# Fix: deducir IGV de ventas para márgenes reales
IGV = Decimal('1.18')
ventas_neto = ventas_total / IGV   # S/100 en vez de S/118
utilidad_bruta = ventas_neto - cogs
margen_bruto_pct = float((utilidad_bruta / ventas_neto * 100) if ventas_neto > 0 else 0)
```

**Impacto:** En una PYME con margen real del 30%, el sistema mostraría ~41%. El dueño creería que le va mejor de lo que realmente está.

---

### BUG-04 — ALTO: Burn rate usa `saldo_actual` del período, no saldo acumulado

**Archivo:** `backend/apps/finanzas/services.py:592-596`

```python
burn_rate_meses = saldo_actual / abs(utilidad_mes)
```

`saldo_actual = cobros_periodo - pagos_periodo` — es el neto del mes actual, **no el cash disponible acumulado**. Una empresa que cobró S/50,000 en meses anteriores pero solo S/1,000 este mes mostraría burn_rate = 0.5 meses, cuando en realidad tiene reservas para mucho más.

**Fix:** Burn rate requiere un campo de "saldo en caja" que el usuario registre manualmente, O desactivarlo por ser engañoso. Recomendación: **eliminar hasta tener un módulo de cuentas bancarias**.

---

### BUG-05 — MEDIO: Aging de compras tiene lógica de signo confusa

**Archivo:** `backend/apps/finanzas/services.py:406-421`

```python
dias_vencimiento = (compra.fecha_vencimiento - self.hoy).days  # positivo = faltan días
dias_atraso = -dias_vencimiento  # positivo = días pasados del vencimiento

if dias_atraso <= 0:        # ← Vigente: incluye dias_atraso=0 (vence HOY)
    aging['vigente'] += saldo
```

Si una compra vence HOY, `dias_vencimiento=0`, `dias_atraso=0`, va a 'vigente'. Correcto. Pero si `fecha_vencimiento=None` (bug de datos), `dias_vencimiento=0` también y va a 'vigente' silenciosamente. **El código no valida que credito compras tengan fecha_vencimiento**.

```python
# Fix: manejar explícitamente el None
if compra.fecha_vencimiento is None:
    aging['vigente'] += saldo  # sin vencimiento definido = asignar a vigente + loguear warning
    logger.warning("Compra %s sin fecha_vencimiento", compra.numero)
    continue
```

---

## PARTE 2 — KPIs que sobran (cortar)

### CORTE-01: `burn_rate_meses` debe eliminarse en v1

El burn rate requiere conocer el **saldo real en cuenta bancaria**, que el sistema no registra. El cálculo actual (`saldo_operativo_del_mes / pérdida_mensual`) es metodológicamente incorrecto y dará cifras alarmantes o ridículas dependiendo del timing de cobros. **Un KPI incorrecto erosiona más la confianza que no tenerlo.**

Reemplazar con: "Tendencia de rentabilidad de los últimos 3 meses" — eso SÍ se puede calcular con los datos disponibles.

---

### CORTE-02: `DPO` (Days Payable Outstanding) es redundante con Aging de proveedores

DPO = cuántos días tardas en pagar. La tabla de aging ya responde esto visualmente. Un dueño de PYME no va a decidir nada diferente si sabe que su DPO es 15 vs 18 días. Lo que sí necesita es la tabla de "qué vence esta semana" — que ya existe. **DPO agrega terminología sin agregar decisiones.**

---

## PARTE 3 — KPIs críticos faltantes

### FALTANTE-01 — URGENTE: IGV por pagar (más importante que DSO para PYME peruana)

**Por qué es crítico:** Las PYMEs bajo Régimen MYPE Tributario declaran IGV trimestralmente. Una PYME que vende S/100,000/mes genera S/18,000/mes de IGV cobrado — y probablemente recupera S/10,000 de IGV de sus compras. Debe declarar S/8,000/mes en impuestos. Si no lo reserva mes a mes, llega la declaración y no tiene el dinero.

**Los datos existen:** `IGVDashboardView` en `dashboard/views.py` ya calcula esto. El módulo de finanzas debería llamar ese endpoint o reutilizar la lógica.

```
IGV por pagar = (Σ Venta.total - Venta.total/1.18) - (Σ Compra.total - Compra.total/1.18)
             = IGV cobrado en ventas - IGV crédito fiscal de compras
```

**Display recomendado:** Card roja si no hay reserva. "Debes reservar S/8,000 para tu declaración del {fecha}."

---

### FALTANTE-02: Capital de trabajo en términos absolutos (no solo ratio)

**Por qué es crítico:** `ratio_liquidez = 1.4x` no le dice nada al dueño. `Capital de trabajo: S/15,200 disponibles` sí.

```
Capital de trabajo = (CxC pendiente + Inventario a precio compra) - CxP pendiente
```

El ratio ya lo tenemos. Añadir el valor absoluto:
```python
capital_trabajo = cxc['total'] + inventario_valor - cxp['total']
```

**Por qué Bain priorizaría esto:** Es la respuesta directa a "¿tengo para operar el mes que viene?" — la pregunta #2 del brief.

---

### FALTANTE-03: Margen histórico (trend de los últimos 6 meses)

**Por qué es crítico:** Un margen del 25% hoy es excelente si estaba en 15% hace 6 meses. Es una crisis silenciosa si estaba en 40%. La foto mensual no da dirección.

```python
# Backend: añadir a calcular_rentabilidad()
historial_margen = []
for i in range(5, -1, -1):
    d = self.fecha_inicio - timedelta(days=30*i)
    # calcular margen para ese mes
    # retornar lista de 6 puntos para sparkline
```

**Display:** Sparkline de 6 meses debajo del card de margen con flecha indicando tendencia.

---

## PARTE 4 — Lo que Bain haría diferente

### 4.1 — "So What?" framing: de métricas a decisiones

El módulo actual responde "¿cuánto?" pero no "¿y qué hago ahora?". Cada KPI crítico debería tener un **action trigger** embebido:

| Métrica actual | Bain la reformularía así |
|---|---|
| `DSO: 22 días` | "3 clientes llevan 30+ días sin pagar (S/12,000). [Enviar recordatorios] [Ver listado]" |
| `Margen: 18% 🟡` | "Tu margen bajó 7pp en 2 meses. Los 3 productos menos rentables son X, Y, Z. [Revisar precios]" |
| `Próximos pagos: S/8,000 esta semana` | "Proveedor X vence el jueves (S/5,000). ¿Tienes fondos? Saldo proyectado: S/3,200. [Negociar plazo]" |
| `Concentración: 62% en 3 clientes` | "Si pierdes a Cliente A, tus ventas caen 38%. [Ver diversificación]" |

---

### 4.2 — Benchmarks contextuales (Perú PYME)

Sin benchmarks, los números flotan en el vacío. Cada métrica clave necesita un referente:

| KPI | Benchmark Perú PYME sugerido |
|---|---|
| DSO | Retail: 15-20d / Servicios: 25-35d / Industrial: 45-60d |
| Margen bruto | Retail productos: 25-40% / Servicios: 45-65% / Manufactura: 20-35% |
| Morosidad | Aceptable <20% / Preocupante 20-35% / Crítico >35% |
| Concentración top 3 | Saludable <40% / Riesgo 40-60% / Crítico >60% |

Mostrar: "Tu DSO es 22 días. PYMEs similares: 15 días. Oportunidad: cobrar 7 días antes libera ~S/4,500/mes."

---

### 4.3 — El "Lunes Financiero" (feature de alto impacto, bajo esfuerzo)

La realidad de los dueños de PYME: **no abren dashboards, leen WhatsApp/email**. El mayor ROI del módulo sería un reporte semanal automatizado cada lunes:

```
📊 Tu semana financiera (26-30 mayo)

💰 Cobros: S/12,400 (3 clientes)
💸 Pagos: S/7,200 (2 proveedores)
📈 Margen esta semana: 34%

⚠️ Esta semana vence:
• Proveedor ABC: S/3,000 (miércoles)

👥 Pendientes de cobro:
• Cliente XYZ: S/5,000 (31 días de atraso)

[Ver dashboard completo]
```

Backend: 1 management command + celery task. Frontend: 0 trabajo adicional.

---

### 4.4 — Semáforo opaco → Semáforo explicado

Actual: "Tu negocio está financieramente saludable" (verde). El dueño no sabe por qué.

Propuesta: El `mensaje` debe incluir el motivo específico más relevante:
```
🟡 Atención requerida
• Tu margen bajó a 18% (mínimo recomendado: 30%)
• 3 clientes llevan 30+ días sin pagar (S/8,500 en riesgo)
✅ Tu liquidez a 30 días es positiva (S/14,200)
```

La puntuación 67/100 no le dice nada. Las 3 líneas de arriba sí.

---

### 4.5 — Empty states como onboarding, no como errores

Un negocio nuevo con 0 ventas verá S/0 en todas partes. Diseño actual: parece roto.

Diseño Bain: cada sección vacía es una **invitación de acción**:
```
Cuentas por cobrar: S/0
→ "Sin ventas a crédito pendientes. 
   Para ver esta sección, registra una venta con tipo de pago 'Crédito 30 días'. 
   [Nueva venta]"
```

---

## PARTE 5 — Problemas técnicos secundarios

### TECH-01: Cache 5 min incluye datos de urgencia

`CACHE_TTL = 5 * 60` aplica a todo el payload. Los **próximos pagos** (que vencen hoy o mañana) necesitan un TTL de 1 minuto, no 5. Si el dueño paga una compra y regresa al módulo 3 minutos después, seguirá viendo la alerta como pendiente.

**Fix:** Cache separado por sección de urgencia:
```python
# Datos urgentes: 1 min
urgentes = {'proximos_pagos': cxp['proximos_pagos'], 'alertas_hoy': ...}
cache.set(f'finanzas:urgente:{empresa.id}', urgentes, 60)

# KPIs estratégicos: 5 min  
cache.set(f'finanzas:kpis:{empresa.id}:{fecha_inicio}:{fecha_fin}', payload, 300)
```

---

### TECH-02: `calcular_crecimiento()` carga todos los cliente_ids en memoria

**Archivo:** `services.py:505-513`

```python
clientes_con_venta_anterior = set(
    Venta.objects
    .filter(empresa=self.empresa, fecha_emision__lt=self.fecha_inicio)
    .values_list('cliente_id', flat=True)
    .distinct()
)  # ← carga TODOS los cliente_ids en memoria Python
```

Para una PYME con 5 años de historial y 1,000+ clientes únicos, esto carga un set grande innecesariamente. Fix usando EXISTS:

```python
nuevos_clientes = (
    ventas_actual_qs
    .filter(cliente__isnull=False)
    .exclude(
        cliente__in=Venta.objects.filter(
            empresa=self.empresa,
            fecha_emision__lt=self.fecha_inicio
        ).values('cliente_id')
    )
    .values('cliente_id')
    .distinct()
    .count()
)
```

---

### TECH-03: COGS puede ser NULL si un producto fue eliminado del catálogo

`F('producto__precio_compra')` en el aggregate retorna NULL si el producto fue borrado después de la venta. El `|| Decimal('0')` solo protege el resultado final del aggregate, no las filas individuales. Si el 30% de las ventas son de productos borrados, el COGS calculado es ficticiamente bajo.

**Fix:**
```python
.annotate(
    precio_compra_safe=Coalesce('producto__precio_compra', Value(Decimal('0')))
)
.aggregate(
    cogs=Sum(F('cantidad') * F('precio_compra_safe'), output_field=DecimalField())
)
```

---

## PARTE 6 — Matriz de prioridades

### Semana 1 — Bugs bloqueantes (arreglar antes de mostrar a usuarios)

| ID | Fix | Impacto | Esfuerzo |
|---|---|---|---|
| BUG-01 | Eliminar llamadas duplicadas en `calcular_avanzados()` | Reduce carga 40% | 30 min |
| BUG-02 | Corregir DSO con rolling 90d | Evita números absurdos | 1h |
| BUG-03 | Deducir IGV de ventas en márgenes | Precisión contable | 30 min |
| CORTE-01 | Eliminar `burn_rate_meses` | Evita datos engañosos | 15 min |

### Semana 2 — Alto impacto, bajo esfuerzo

| ID | Feature | Impacto usuario | Esfuerzo |
|---|---|---|---|
| FALTANTE-01 | IGV por pagar (reutiliza IGVDashboardView) | CRÍTICO para PYME peruana | 2h |
| FALTANTE-02 | Capital de trabajo absoluto | Responde "¿tengo para el mes?" | 1h |
| 4.4 | Semáforo con razón específica | Confianza en la herramienta | 2h |
| TECH-01 | Cache separado para urgencias | UX coherente post-pago | 1h |

### Semana 3 — Diferenciadores competitivos

| ID | Feature | Impacto negocio | Esfuerzo |
|---|---|---|---|
| 4.3 | Lunes Financiero (email digest semanal) | Retención + engagement | 1 día |
| FALTANTE-03 | Historial de margen 6 meses | Decisiones de pricing | 3h |
| 4.1 | Action triggers en morosos (botón "Cobrar" con pre-fill) | Convierte insight en acción | 4h |
| 4.2 | Benchmarks contextuales por sector | Trust + autoridad | 2h |

### v2 — Expansiones estratégicas (no urgentes)

- WhatsApp API para cobros automáticos a clientes morosos
- Proyección de flujo 90 días basada en histórico + contratos recurrentes
- Módulo de cuentas bancarias (para burn rate real)
- "Modo contador": exportar PDF con formato sunat-compatible

---

## Resumen ejecutivo para el fundador

**Lo que está bien:** Estructura del módulo, selección inicial de KPIs, aging tables, semáforo general, top productos. La arquitectura de servicios es limpia y extensible.

**Lo que rompería la confianza del usuario si sale ahora:**
1. DSO absurdo a mitad de mes (BUG-02)
2. Márgenes sobreestimados 8-10% por IGV (BUG-03)
3. Burn rate con números sin sentido (BUG-04/CORTE-01)
4. Duplicación de queries que hace la página lenta (BUG-01)

**El diferenciador que haría viral el módulo en Perú:** IGV por pagar. Ningún ERP para PYME peruana lo muestra en tiempo real. Cada dueño de negocio en Perú tiene miedo de SUNAT. Si este módulo responde "debes reservar S/8,200 para tu declaración del 20 de junio" — eso es el hook que hace que lo usen semanalmente.

**La frase que resume qué cambiar:** El módulo actual habla el lenguaje de un CFO. Necesita hablar el lenguaje del dueño de una bodega en Miraflores: "¿Tengo para pagar el viernes? ¿Me está yendo bien este mes? ¿Quién me debe plata?"

---

*Generado con `/plan-ceo-review` (gstack) · 2026-05-30 · Modo: SELECTIVE EXPANSION*
