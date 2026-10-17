"""
Eval de selección de herramienta: corre las preguntas de `evals/preguntas.yaml`
contra un modelo real y mide, por pregunta, si el modelo elige la tool correcta y los
parámetros esperados, además de latencia, tokens y costo estimado.

Uso:
    python manage.py eval_llm --model gemini-3.1-flash-lite
    python manage.py eval_llm --model gemini-2.5-flash-lite --repeticiones 2
    python manage.py eval_llm --model gpt-4o-mini --provider openai

Las tools NO se ejecutan (modo `ejecutar_tools=False`): no se escribe nada en ventas
ni compras. Toda la BD de la corrida (conversaciones, mensajes, uso) se revierte al
final (transacción con rollback), así que el comando no deja rastro. Requiere ADC
para Vertex (`gcloud auth application-default login`) y BD local con `seed_demo`.
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

# USD por 1M tokens (entrada, salida). Fuente: página oficial de precios de la API
# Gemini (tarifa estándar, texto), consultada 2026-10-16.
PRECIOS = {
    'gemini-3.1-flash-lite': (0.25, 1.50),
    'gemini-2.5-flash-lite': (0.10, 0.40),
}


class _Rollback(Exception):
    pass


def _coincide(esperado, real) -> bool:
    if isinstance(esperado, dict):
        if 'en' in esperado:
            return any(_coincide(e, real) for e in esperado['en'])
        if 'contiene' in esperado:
            return isinstance(real, str) and str(esperado['contiene']).lower() in real.lower()
        if 'presente' in esperado:
            return (real is not None and real != '') if esperado['presente'] else real in (None, '')
        return esperado == real
    if isinstance(esperado, str) and isinstance(real, str):
        return esperado.lower() == real.lower()
    return esperado == real


def _percentil(valores, p):
    if not valores:
        return 0
    vs = sorted(valores)
    k = max(0, min(len(vs) - 1, round((p / 100) * (len(vs) - 1))))
    return vs[k]


class Command(BaseCommand):
    help = 'Eval de selección de tool del asistente contra un modelo real (sin ejecutar tools).'

    def add_arguments(self, parser):
        parser.add_argument('--model', required=True)
        parser.add_argument('--provider', default=None, help='vertex (default) u openai')
        parser.add_argument('--preguntas', default='evals/preguntas.yaml')
        parser.add_argument('--repeticiones', type=int, default=1)
        parser.add_argument('--salida', default=None, help='JSON de resultados (default: evals/resultados/<model>_<ts>.json)')
        parser.add_argument('--solo', default=None, help='ids separados por coma, p. ej. q01,q05')

    def handle(self, *args, **o):
        host = str(connection.settings_dict.get('HOST', '')).lower()
        if 'supabase' in host or 'pooler' in host:
            raise CommandError(f'ABORTADO: la BD no es local (HOST={host}).')

        base = Path(settings.BASE_DIR)
        ruta = base / o['preguntas']
        spec = yaml.safe_load(ruta.read_text(encoding='utf-8'))
        preguntas = spec['preguntas']
        if o['solo']:
            ids = set(o['solo'].split(','))
            preguntas = [p for p in preguntas if p['id'] in ids]

        from django.contrib.auth import get_user_model
        from apps.ai_assistant.services.chat import AsistenteChat, crear_conversacion
        from apps.ai_assistant.services.llm_client import LLMError, get_llm_client
        from apps.ai_assistant.services.perfiles import get_perfil

        User = get_user_model()
        user = User.objects.filter(email=spec['usuario']).select_related('empresa').first()
        if not user or not user.empresa or user.empresa.ruc != str(spec['empresa_ruc']):
            raise CommandError('Usuario/empresa del eval no encontrados. Corre: python manage.py seed_demo')

        cliente = get_llm_client(modelo=o['model'], proveedor=o['provider'])
        self.stdout.write(f"Modelo: {o['model']}  proveedor: {cliente.proveedor}  "
                          f"location: {getattr(cliente, 'location', '-')}  preguntas: {len(preguntas)} "
                          f"x{o['repeticiones']}")

        filas = []
        try:
            with transaction.atomic():
                for rep in range(o['repeticiones']):
                    for p in preguntas:
                        filas.append(self._correr(p, rep, user, cliente, crear_conversacion, AsistenteChat,
                                                  get_perfil, LLMError))
                raise _Rollback()
        except _Rollback:
            pass

        resumen = self._resumen(o['model'], filas)
        self._imprimir(filas, resumen)
        salida = Path(o['salida']) if o['salida'] else base / 'evals' / 'resultados' / \
            f"{o['model']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps({'modelo': o['model'], 'proveedor': cliente.proveedor,
                                      'resumen': resumen, 'filas': filas}, ensure_ascii=False, indent=1, default=str))
        self.stdout.write(self.style.SUCCESS(f'Resultados: {salida}'))

    # ------------------------------------------------------------------
    def _correr(self, p, rep, user, cliente, crear_conversacion, AsistenteChat, get_perfil, LLMError):
        perfil = get_perfil(p.get('perfil', 'jorge'))
        conv = crear_conversacion(user, perfil, titulo=f"eval {p['id']}")
        chat = AsistenteChat(conv, perfil, cliente=cliente, ejecutar_tools=False)
        fila = {'id': p['id'], 'rep': rep, 'perfil': perfil.clave, 'esperado_tool': p.get('tool'),
                'tool': None, 'params': None, 'tool_ok': False, 'params_ok': False, 'error': None,
                'latencia_ms': 0, 'tokens_in': 0, 'tokens_out': 0, 'respuesta_len': 0}
        t0 = time.monotonic()
        try:
            texto = chat.enviar(p['pregunta'])
        except LLMError as e:
            fila['error'] = f'{type(e).__name__}: {getattr(e, "detalle", "")}'
            fila['latencia_ms'] = int((time.monotonic() - t0) * 1000)
            return fila
        tr = chat.traza
        fila.update(latencia_ms=tr.latencia_primera_ms or int((time.monotonic() - t0) * 1000),
                    tokens_in=tr.tokens_entrada, tokens_out=tr.tokens_salida, respuesta_len=len(texto or ''))
        primera = tr.tool_calls[0] if tr.tool_calls else None
        fila['tool'] = primera.name if primera else None
        fila['params'] = primera.arguments if primera else None
        esperado = p.get('tool')
        prohibida = p.get('tool_prohibida')
        llamadas = {t.name for t in tr.tool_calls}
        if prohibida and prohibida in llamadas:
            fila['tool_ok'] = False
        elif esperado is None:
            fila['tool_ok'] = primera is None
        else:
            fila['tool_ok'] = _coincide(esperado, fila['tool'])
        if fila['tool_ok'] and primera is not None:
            fila['params_ok'] = all(_coincide(v, (primera.arguments or {}).get(k)) for k, v in (p.get('params') or {}).items())
        elif fila['tool_ok'] and primera is None:
            fila['params_ok'] = True  # no había que llamar nada
        return fila

    @staticmethod
    def _resumen(modelo, filas):
        validas = [f for f in filas if not f['error']]
        n = len(filas)
        lat = [f['latencia_ms'] for f in validas]
        t_in = sum(f['tokens_in'] for f in validas)
        t_out = sum(f['tokens_out'] for f in validas)
        precio = PRECIOS.get(modelo)
        costo = (t_in * precio[0] + t_out * precio[1]) / 1_000_000 if precio else None
        return {
            'preguntas': n, 'errores': n - len(validas),
            'tool_correcta_pct': round(100 * sum(f['tool_ok'] for f in filas) / n, 1) if n else 0,
            'params_correctos_pct': round(100 * sum(f['params_ok'] for f in filas) / n, 1) if n else 0,
            'latencia_p50_ms': int(statistics.median(lat)) if lat else 0,
            'latencia_p95_ms': int(_percentil(lat, 95)),
            'tokens_in': t_in, 'tokens_out': t_out,
            'costo_usd_corrida': round(costo, 6) if costo is not None else None,
            'costo_usd_por_1000_preguntas': round(costo / n * 1000, 4) if (costo is not None and n) else None,
        }

    def _imprimir(self, filas, r):
        self.stdout.write('')
        self.stdout.write(f"{'id':<5} {'perfil':<8} {'esperado':<34} {'obtenido':<22} {'tool':<5} {'params':<6} {'ms':>6} {'tok':>9}")
        for f in filas:
            esp = f['esperado_tool'] if not isinstance(f['esperado_tool'], dict) else '|'.join(f['esperado_tool'].get('en', []))
            self.stdout.write(f"{f['id']:<5} {f['perfil']:<8} {str(esp):<34} {str(f['tool']):<22} "
                              f"{'OK' if f['tool_ok'] else 'X':<5} {'OK' if f['params_ok'] else 'X':<6} "
                              f"{f['latencia_ms']:>6} {f['tokens_in']:>4}/{f['tokens_out']:<4} {f['error'] or ''}")
        self.stdout.write('')
        self.stdout.write(f"tool correcta: {r['tool_correcta_pct']}%   params correctos: {r['params_correctos_pct']}%   "
                          f"errores: {r['errores']}")
        self.stdout.write(f"latencia p50: {r['latencia_p50_ms']} ms   p95: {r['latencia_p95_ms']} ms   "
                          f"tokens in/out: {r['tokens_in']}/{r['tokens_out']}   "
                          f"costo corrida: {r['costo_usd_corrida']} USD   por 1000 preguntas: {r['costo_usd_por_1000_preguntas']} USD")
