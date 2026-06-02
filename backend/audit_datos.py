import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ventas.models import Venta, DetalleVenta
from apps.compras.models import Compra, CompraDetalle
from apps.inventario.models.producto import Producto
from decimal import Decimal

empresa_id = 1  # ajustar al ID real de la empresa

print("=" * 70)
print("AUDITORÍA DE DATOS - ERP SYSTEM")
print("=" * 70)

# ── EMPRESAS ──────────────────────────────────────────────────────────────
from apps.empresas.models import Empresa
empresas = Empresa.objects.all()
print(f"\nEMPRESAS EN BD: {empresas.count()}")
for e in empresas:
    print(f"  ID={e.id} | {e.nombre} | RUC={e.ruc}")

# Confirmar ID correcto
empresa = Empresa.objects.first()
empresa_id = empresa.id
print(f"\n>>> Usando empresa_id={empresa_id}: {empresa.nombre}")

print("\n" + "=" * 70)
print("VENTAS")
print("=" * 70)

ventas = Venta.objects.filter(empresa_id=empresa_id)
print(f"\nVENTAS TOTAL: {ventas.count()}")

print(f"\nPor moneda:")
for moneda in ['PEN', 'USD']:
    v = ventas.filter(moneda=moneda)
    totales = list(v.values_list('total', flat=True))
    total = sum(float(t) for t in totales)
    print(f"  {moneda}: {v.count()} ventas, total={total:,.2f}")

print(f"\nPor estado:")
for estado in ['pagado', 'pendiente', 'borrador', 'anulado']:
    v = ventas.filter(estado=estado)
    totales = list(v.values_list('total', flat=True))
    total = sum(float(t) for t in totales)
    print(f"  {estado}: {v.count()} ventas, total={total:,.2f}")

print(f"\nÚltimas 10 ventas (más recientes):")
for v in ventas.order_by('-fecha_emision')[:10]:
    print(f"  {v.numero} | {v.moneda} | total={float(v.total):,.2f} | {v.estado} | {v.fecha_emision}")

# Ventas del mes actual
from django.utils import timezone
from datetime import datetime
hoy = timezone.now()
primer_dia = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
ventas_mes = ventas.filter(fecha_emision__gte=primer_dia.date())
print(f"\nVentas del mes actual ({hoy.strftime('%B %Y')}): {ventas_mes.count()}")
for v in ventas_mes.order_by('fecha_emision'):
    print(f"  {v.numero} | {v.moneda} | total={float(v.total):,.2f} | {v.estado} | {v.fecha_emision}")

print("\n" + "=" * 70)
print("COMPRAS")
print("=" * 70)

compras = Compra.objects.filter(empresa_id=empresa_id)
print(f"\nCOMPRAS TOTAL: {compras.count()}")

print(f"\nPor moneda:")
for moneda in ['PEN', 'USD']:
    c = compras.filter(moneda=moneda)
    totales = list(c.values_list('total', flat=True))
    total = sum(float(t) for t in totales)
    print(f"  {moneda}: {c.count()} compras, total={total:,.2f}")

print(f"\nPor estado:")
for estado in ['pagada', 'pendiente', 'borrador', 'anulada']:
    c = compras.filter(estado=estado)
    totales = list(c.values_list('total', flat=True))
    total = sum(float(t) for t in totales)
    print(f"  {estado}: {c.count()} compras, total={total:,.2f}")

print(f"\nÚltimas 10 compras (más recientes):")
for c in compras.order_by('-fecha_emision')[:10]:
    print(f"  {c.numero} | {c.moneda} | total={float(c.total):,.2f} | {c.estado} | {c.fecha_emision}")

# Compras del mes actual
compras_mes = compras.filter(fecha_emision__gte=primer_dia.date())
print(f"\nCompras del mes actual ({hoy.strftime('%B %Y')}): {compras_mes.count()}")
for c in compras_mes.order_by('fecha_emision'):
    print(f"  {c.numero} | {c.moneda} | total={float(c.total):,.2f} | {c.estado} | {c.fecha_emision}")

print("\n" + "=" * 70)
print("DETALLES DE COMPRA")
print("=" * 70)

try:
    detalles_compra = CompraDetalle.objects.filter(compra__empresa_id=empresa_id)
    print(f"\nDETALLES DE COMPRA: {detalles_compra.count()}")
    precios = [float(p) for p in detalles_compra.values_list('precio_unitario', flat=True) if p is not None]
    if precios:
        print(f"  Precio unitario min:  {min(precios):.4f}")
        print(f"  Precio unitario max:  {max(precios):.4f}")
        print(f"  Precio unitario prom: {sum(precios)/len(precios):.4f}")
        precios_cero = [p for p in precios if p < 0.01]
        print(f"  Precios < 0.01:       {len(precios_cero)} ({len(precios_cero)/len(precios)*100:.1f}%)")
    else:
        print("  Sin datos de precios")

    print(f"\nPrimeros 10 detalles de compra:")
    for d in detalles_compra[:10]:
        print(f"  Compra #{d.compra.numero} | {d.producto.nombre if d.producto else 'N/A'} | qty={d.cantidad} | precio={float(d.precio_unitario):.4f} | subtotal={float(d.subtotal):.4f}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("DETALLES DE VENTA")
print("=" * 70)

try:
    detalles_venta = DetalleVenta.objects.filter(venta__empresa_id=empresa_id)
    print(f"\nDETALLES DE VENTA: {detalles_venta.count()}")
    precios_v = [float(p) for p in detalles_venta.values_list('precio_unitario', flat=True) if p is not None]
    if precios_v:
        print(f"  Precio unitario min:  {min(precios_v):.4f}")
        print(f"  Precio unitario max:  {max(precios_v):.4f}")
        print(f"  Precio unitario prom: {sum(precios_v)/len(precios_v):.4f}")
    else:
        print("  Sin datos de precios")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("VERIFICACIÓN DE INTEGRIDAD — ¿Totales cuadran con detalles?")
print("=" * 70)

ventas_con_detalles = 0
ventas_sin_detalles = 0
ventas_descuadradas = []

for v in ventas[:20]:
    try:
        detalles = v.detalles.all()
        if detalles.count() == 0:
            ventas_sin_detalles += 1
        else:
            ventas_con_detalles += 1
            total_detalles = sum(float(d.subtotal) for d in detalles)
            diff = abs(float(v.total) - total_detalles)
            cuadra = diff < 0.02
            if not cuadra:
                ventas_descuadradas.append(v)
            print(f"  Venta {v.numero}: total={float(v.total):.2f} | suma_detalles={total_detalles:.2f} | diff={diff:.2f} | {'OK' if cuadra else 'DESCUADRA'}")
    except Exception as e:
        print(f"  Venta {v.numero}: ERROR - {e}")

print(f"\nResumen integridad ventas (primeras 20):")
print(f"  Con detalles: {ventas_con_detalles}")
print(f"  Sin detalles: {ventas_sin_detalles}")
print(f"  Descuadradas: {len(ventas_descuadradas)}")

print("\n" + "=" * 70)
print("DASHBOARD — ¿Qué vería el usuario?")
print("=" * 70)

# Simular cálculo del dashboard
tc = 3.80  # fallback

ventas_pagadas = ventas.filter(estado='pagado')
compras_pagadas = compras.filter(estado='pagada')

ventas_pen = sum(float(v.total) for v in ventas_pagadas if v.moneda == 'PEN')
ventas_usd = sum(float(v.total) for v in ventas_pagadas if v.moneda == 'USD')
ventas_total_pen = ventas_pen + ventas_usd * tc

compras_pen = sum(float(c.total) for c in compras_pagadas if c.moneda == 'PEN')
compras_usd = sum(float(c.total) for c in compras_pagadas if c.moneda == 'USD')
compras_total_pen = compras_pen + compras_usd * tc

print(f"\nVentas pagadas total histórico:")
print(f"  PEN: {ventas_pen:,.2f}")
print(f"  USD: {ventas_usd:,.2f} × {tc} = {ventas_usd*tc:,.2f} PEN")
print(f"  TOTAL en PEN: {ventas_total_pen:,.2f}")

print(f"\nCompras pagadas total histórico:")
print(f"  PEN: {compras_pen:,.2f}")
print(f"  USD: {compras_usd:,.2f} × {tc} = {compras_usd*tc:,.2f} PEN")
print(f"  TOTAL en PEN: {compras_total_pen:,.2f}")

if ventas_total_pen > 0:
    utilidad = (ventas_total_pen / 1.18) - (compras_total_pen / 1.18)
    margen = utilidad / (ventas_total_pen / 1.18) * 100
    print(f"\nUtilidad calculada (ventas_sin_igv - compras_sin_igv):")
    print(f"  ventas/1.18 = {ventas_total_pen/1.18:,.2f}")
    print(f"  compras/1.18 = {compras_total_pen/1.18:,.2f}")
    print(f"  UTILIDAD = {utilidad:,.2f}")
    print(f"  MARGEN   = {margen:.1f}%")

    if compras_total_pen < 1.0:
        print(f"\n  ⚠️  ALERTA: Compras totales < S/1.00 — los precios de compra están en $0.01")
        print(f"      Esto hace que la utilidad = ventas casi al 100%, lo cual es INCORRECTO")

# Por cobrar (ventas pendientes)
ventas_pendientes = ventas.filter(estado='pendiente')
pc_pen = sum(float(v.total) for v in ventas_pendientes if v.moneda == 'PEN')
pc_usd = sum(float(v.total) for v in ventas_pendientes if v.moneda == 'USD')
por_cobrar = pc_pen + pc_usd * tc

# Por pagar (compras pendientes)
compras_pendientes = compras.filter(estado='pendiente')
pp_pen = sum(float(c.total) for c in compras_pendientes if c.moneda == 'PEN')
pp_usd = sum(float(c.total) for c in compras_pendientes if c.moneda == 'USD')
por_pagar = pp_pen + pp_usd * tc

print(f"\nPor Cobrar (ventas pendientes): S/ {por_cobrar:,.2f} ({ventas_pendientes.count()} ventas)")
print(f"Por Pagar  (compras pendientes): S/ {por_pagar:,.2f} ({compras_pendientes.count()} compras)")

print("\n" + "=" * 70)
print("DIAGNÓSTICO FINAL")
print("=" * 70)

issues = []

if compras_total_pen < 1.0 and compras.count() > 0:
    issues.append("CRÍTICO: Compras importadas tienen total ~$0.01, utilidad está inflada artificialmente")

ventas_usd_count = ventas.filter(moneda='USD').count()
if ventas_usd_count > 0:
    issues.append(f"INFO: {ventas_usd_count} ventas en USD — la conversión TC={tc} ya está implementada en el dashboard")

# Verificar si hay ventas con misma fecha (evidencia de importación masiva)
from django.db.models import Count as DCount
fechas_repetidas = ventas.values('fecha_emision').annotate(cnt=DCount('id')).filter(cnt__gt=10).order_by('-cnt')
for f in fechas_repetidas[:5]:
    issues.append(f"INFO: {f['cnt']} ventas con fecha {f['fecha_emision']} — posible importación masiva")

fechas_compras_rep = compras.values('fecha_emision').annotate(cnt=DCount('id')).filter(cnt__gt=5).order_by('-cnt')
for f in fechas_compras_rep[:5]:
    issues.append(f"INFO: {f['cnt']} compras con fecha {f['fecha_emision']} — posible importación masiva")

if issues:
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue}")
else:
    print("\nNo se encontraron problemas críticos de integridad.")

print("\n" + "=" * 70)
