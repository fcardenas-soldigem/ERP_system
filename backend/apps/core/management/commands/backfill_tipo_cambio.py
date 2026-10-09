"""
Backfill de tipo_cambio histórico para documentos USD sin TC guardado.

Reemplaza a las data migrations (ahora no-op): una migración no debe depender
de una API externa. Este comando es idempotente y reintentable — si una fecha
falla, queda null y se rellena en la próxima corrida.

Uso:
    python manage.py backfill_tipo_cambio            # ejecuta
    python manage.py backfill_tipo_cambio --dry-run  # solo cuenta, sin API

Los documentos PEN con tipo_cambio null también se normalizan a 1.0 (sin red).
"""
import time

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.services.tipo_cambio import get_tc_venta

# (app_label.Model, campo de fecha) — los 5 modelos con moneda + tipo_cambio
MODELOS = [
    ('ventas.Venta', 'fecha_emision'),
    ('compras.Compra', 'fecha_emision'),
    ('compras.OrdenCompra', 'fecha_emision'),
    ('compras.OrdenServicioCompra', 'fecha_emision'),
    ('cotizaciones.Cotizacion', 'fecha_emision'),
]

PAUSA_ENTRE_LLAMADAS = 0.5  # seg — respeto del rate limit de apis.net.pe


class Command(BaseCommand):
    help = 'Rellena tipo_cambio histórico (SBS por fecha_emision) en docs USD con tipo_cambio null. Idempotente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra cuántos documentos y fechas distintas procesaría. No llama a la API ni escribe.',
        )

    def handle(self, *args, **options):
        from django.apps import apps as django_apps

        host = str(connection.settings_dict.get('HOST', '')).lower()
        self.stdout.write(f'BD: {host or "localhost"} / {connection.settings_dict.get("NAME")}')

        dry_run = options['dry_run']

        # ── Fase 1: inventario — docs pendientes y fechas distintas (sin API) ──
        plan = []           # (Model, fecha_field, qs_usd_null)
        fechas_global = {}  # fecha -> total docs (entre TODOS los modelos)
        total_pen_null = 0
        total_usd_null = 0

        for label, fecha_field in MODELOS:
            Model = django_apps.get_model(label)
            pendientes = Model.objects.filter(tipo_cambio__isnull=True)
            n_pen = pendientes.filter(moneda='PEN').count()
            usd = pendientes.filter(moneda='USD')
            n_usd = usd.count()
            total_pen_null += n_pen
            total_usd_null += n_usd
            fechas_modelo = list(usd.values_list(fecha_field, flat=True).distinct())
            for f in fechas_modelo:
                fechas_global[f] = fechas_global.get(f, 0) + usd.filter(**{fecha_field: f}).count()
            plan.append((label, Model, fecha_field, usd))
            self.stdout.write(
                f'  {label}: {n_usd} USD null ({len(fechas_modelo)} fechas), {n_pen} PEN null'
            )

        self.stdout.write(
            f'\nTOTAL: {total_usd_null} docs USD null · {len(fechas_global)} fechas distintas '
            f'(= llamadas a la API) · {total_pen_null} docs PEN null (sin red)'
        )

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY-RUN: no se llamó a la API ni se escribió nada.'))
            return

        # ── Fase 2: PEN → 1.0 (bulk, sin red) ──
        actualizados_pen = 0
        for label, Model, fecha_field, _ in plan:
            actualizados_pen += Model.objects.filter(
                tipo_cambio__isnull=True, moneda='PEN',
            ).update(tipo_cambio=Decimal('1.0'))

        # ── Fase 3: UN cache de TC por fecha, compartido entre los 5 modelos ──
        # Una sola llamada por fecha distinta; get_tc_venta ya retrocede al día
        # hábil anterior en fines de semana/feriados y cachea en Django cache.
        tc_por_fecha = {}
        fechas_fallidas = []
        fechas_ordenadas = sorted(f for f in fechas_global if f is not None)

        for i, fecha in enumerate(fechas_ordenadas):
            try:
                tc = get_tc_venta(fecha)
            except Exception as e:  # noqa: BLE001 — nunca abortar el backfill
                self.stderr.write(f'  ✗ {fecha}: error inesperado ({e}) — se deja null, continúo')
                tc = None
            if tc is not None:
                tc_por_fecha[fecha] = tc
            else:
                fechas_fallidas.append(fecha)
                self.stderr.write(f'  ✗ {fecha}: sin TC — {fechas_global[fecha]} doc(s) quedan null')
            if i < len(fechas_ordenadas) - 1:
                time.sleep(PAUSA_ENTRE_LLAMADAS)

        # ── Fase 4: aplicar el cache a los 5 modelos ──
        actualizados_usd = 0
        fallidos_usd = 0
        for label, Model, fecha_field, usd in plan:
            for fecha, tc in tc_por_fecha.items():
                actualizados_usd += usd.filter(**{fecha_field: fecha}).update(tipo_cambio=tc)
            for fecha in fechas_fallidas:
                fallidos_usd += usd.filter(**{fecha_field: fecha}).count()

        # ── Resumen ──
        self.stdout.write('\n── Resumen ──')
        self.stdout.write(f'  Actualizados: {actualizados_usd} USD + {actualizados_pen} PEN')
        self.stdout.write(f'  Fallidos (quedan null): {fallidos_usd}')
        if fechas_fallidas:
            self.stdout.write('  Fechas que fallaron: ' + ', '.join(str(f) for f in fechas_fallidas))
            self.stdout.write(self.style.WARNING(
                'Reintenta más tarde con el mismo comando (idempotente: solo toca los null).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Sin fallos.'))
        # Exit code 0 SIEMPRE: los fallos se resuelven re-corriendo, no rompiendo el pipeline.
