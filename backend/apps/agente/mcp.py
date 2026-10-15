"""
Endpoint MCP remoto: JSON-RPC 2.0 sobre HTTP (Streamable HTTP con respuesta JSON
única, compatible con gunicorn WSGI — sin SSE).

Métodos: initialize, tools/list, tools/call. Solo autenticado por ApiToken (Bearer),
rate-limit por token. Cada `tools/call` queda registrado en AgenteAccionLog.
"""
import json
import time

from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import ApiTokenAuthentication, EsTokenMCP
from .models import AgenteAccionLog
from .throttling import MCPTokenThrottle
from .tools import TOOLS, run_tool, tools_list

PROTOCOL_VERSION = '2024-11-05'
SERVER_INFO = {'name': 'soldigem-erp', 'version': '1.0.0'}


def _result(rpc_id, result):
    return {'jsonrpc': '2.0', 'id': rpc_id, 'result': result}


def _error(rpc_id, code, message):
    return {'jsonrpc': '2.0', 'id': rpc_id, 'error': {'code': code, 'message': message}}


def _sanear(args):
    """Deja solo escalares acotados en los argumentos que se guardan en el log."""
    out = {}
    for k, v in (args or {}).items():
        if isinstance(v, str):
            out[k] = v[:200]
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = '<omitido>'
    return out


class MCPView(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [EsTokenMCP]
    throttle_classes = [MCPTokenThrottle]

    def post(self, request):
        body = request.data if isinstance(request.data, dict) else {}
        rpc_id = body.get('id')
        method = body.get('method')
        params = body.get('params') or {}

        if method == 'initialize':
            return Response(_result(rpc_id, {
                'protocolVersion': PROTOCOL_VERSION,
                'capabilities': {'tools': {}},
                'serverInfo': SERVER_INFO,
            }))

        if method == 'notifications/initialized':
            return Response(status=202)  # notificación: sin cuerpo de respuesta

        if method == 'tools/list':
            return Response(_result(rpc_id, {'tools': tools_list()}))

        if method == 'tools/call':
            name = params.get('name')
            arguments = params.get('arguments') or {}
            if name not in TOOLS:
                return Response(_error(rpc_id, -32602, f'Herramienta desconocida: {name}'))

            t0 = time.monotonic()
            ok, resumen = True, ''
            try:
                result, resumen = run_tool(name, request.empresa, arguments)
                rpc = _result(rpc_id, {'content': [
                    {'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}]})
            except Exception as exc:  # noqa: BLE001 — se registra y se devuelve isError
                ok, resumen = False, str(exc)[:200]
                rpc = _result(rpc_id, {'content': [
                    {'type': 'text', 'text': f'Error: {exc}'}], 'isError': True})
            finally:
                AgenteAccionLog.objects.create(
                    empresa=request.empresa,
                    token=request.auth,
                    herramienta=name or '',
                    argumentos=_sanear(arguments),
                    resultado_resumen=resumen,
                    ok=ok,
                    duracion_ms=int((time.monotonic() - t0) * 1000),
                )
            return Response(rpc)

        return Response(_error(rpc_id, -32601, f'Método no soportado: {method}'))
