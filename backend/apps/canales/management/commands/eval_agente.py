"""
C11 — corre los 15 mensajes del eval contra el LLM REAL configurado
(LLM_PROVIDER, credenciales de Vertex/ADC) y reporta tool y parámetros.

    python manage.py eval_agente          # todos
    python manage.py eval_agente --caso 3 # uno

No toca la BD: solo mide al intérprete. Umbral de aprobación: 13/15 (87 %).
"""
from django.core.management.base import BaseCommand

from apps.canales.eval.mensajes import CASOS, comparar
from apps.canales.nucleo.interprete import interpretar

UMBRAL = 13


class Command(BaseCommand):
    help = 'Evalúa el intérprete del bot con 15 mensajes reales (LLM real).'

    def add_arguments(self, parser):
        parser.add_argument('--caso', type=int, default=None)

    def handle(self, *args, **opts):
        casos = [c for c in CASOS if opts['caso'] in (None, c['id'])]
        aciertos = 0
        for caso in casos:
            try:
                tool, entrada, _ = interpretar(caso['texto'])
            except Exception as e:  # credenciales, red…
                self.stderr.write(self.style.ERROR(f'#{caso["id"]:>2} ERROR: {e}'))
                continue
            ok, detalle = comparar(caso, tool, entrada)
            aciertos += ok
            estilo = self.style.SUCCESS if ok else self.style.ERROR
            self.stdout.write(estilo(f'#{caso["id"]:>2} {"✓" if ok else "✗"} «{caso["texto"][:48]}…» → {tool} · {detalle}'))
        total = len(casos)
        self.stdout.write(f'\n{aciertos}/{total} correctos')
        if total == len(CASOS) and aciertos < UMBRAL:
            self.stderr.write(self.style.ERROR(f'Por debajo del umbral ({UMBRAL}/{len(CASOS)}).'))
            raise SystemExit(1)
