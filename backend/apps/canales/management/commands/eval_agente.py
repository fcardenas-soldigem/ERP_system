"""
Eval de punta a punta del bot contra el LLM REAL configurado (LLM_PROVIDER,
credenciales de Vertex/ADC). Puntos 3 y 4.

    python manage.py eval_agente                      # todos los casos
    python manage.py eval_agente --caso 8             # uno
    python manage.py eval_agente --email otra@empresa # otro usuario de prueba

Corre el MISMO bucle de tools que el bot (máx. 5 rondas) sobre la empresa del
usuario de seed_demo, con clientes/productos/ventas del eval creados dentro de
una transacción que SIEMPRE se revierte: no queda nada en la BD.

Por caso: correcto / parcial / incorrecto, rondas, latencia y tokens.
Umbral: 13/15 correctos (proporcional al número de casos).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.canales.eval.mensajes import CASOS, umbral
from apps.canales.eval.runner import evaluar, preparar_datos

ICONO = {'correcto': '✓', 'parcial': '◐', 'incorrecto': '✗'}


class Command(BaseCommand):
    help = 'Eval de punta a punta del bot con el LLM real (transacción revertida).'

    def add_arguments(self, parser):
        parser.add_argument('--caso', type=int, default=None)
        parser.add_argument('--email', default='demo-constock@local.dev',
                            help='usuario de seed_demo (admin) sobre cuya empresa corre el eval')

    def handle(self, *args, **opts):
        usuario = get_user_model().objects.filter(email=opts['email']).select_related('empresa').first()
        if not usuario or not usuario.empresa:
            raise CommandError(f'No existe {opts["email"]} con empresa. Corre antes: python manage.py seed_demo')
        casos = [c for c in CASOS if opts['caso'] in (None, c['id'])]
        if not casos:
            raise CommandError(f'No hay caso {opts["caso"]}.')

        with transaction.atomic():
            preparar_datos(usuario.empresa)
            resultados = evaluar(usuario, casos)
            transaction.set_rollback(True)   # SIEMPRE: el eval no deja rastro

        for r in resultados:
            estilo = {'correcto': self.style.SUCCESS, 'parcial': self.style.WARNING}.get(r.estado, self.style.ERROR)
            self.stdout.write(estilo(
                f'#{r.id:>2} {ICONO[r.estado]} {r.estado:<10} final={r.final:<26} '
                f'rondas={r.rondas} {r.ms:>5} ms {r.tokens:>6} tok  «{r.texto[:45]}»'))
            for f in r.fallos:
                self.stdout.write(f'      · {f}')

        n = len(resultados)
        correctos = sum(r.estado == 'correcto' for r in resultados)
        parciales = sum(r.estado == 'parcial' for r in resultados)
        ms = sum(r.ms for r in resultados)
        tokens = sum(r.tokens for r in resultados)
        self.stdout.write(
            f'\n{correctos}/{n} correctos · {parciales} parciales · {n - correctos - parciales} incorrectos'
            f' · latencia total {ms / 1000:.1f} s (media {ms / max(n, 1):.0f} ms) · {tokens} tokens')
        if opts['caso'] is None:
            minimo = umbral(n)
            if correctos < minimo:
                self.stderr.write(self.style.ERROR(f'Por debajo del umbral ({minimo}/{n}).'))
                raise SystemExit(1)
            self.stdout.write(self.style.SUCCESS(f'Umbral superado ({minimo}/{n}).'))
