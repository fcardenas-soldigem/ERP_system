"""
Conversión de modelos pydantic → `ToolSpec` con un JSON Schema que aceptan tanto
Gemini (function declarations, subconjunto OpenAPI 3.0: SIN $ref/$defs, SIN title,
SIN default; `anyOf [X, null]` → `nullable`) como la API `chat.completions`.

Antes se usaba `openai.pydantic_function_tool`, que ata la definición a un
proveedor. Las clases pydantic de `tools/*.py` siguen siendo la fuente de verdad.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from typing import Type

from pydantic import BaseModel

from .llm_client import ToolSpec

# Claves que emitimos. Además se intersectan con las que el SDK instalado
# de google-genai acepta en `types.Schema` (extra='forbid'): si una versión
# futura quita alguna, se descarta en vez de romper la llamada.
_CLAVES_PERMITIDAS = {
    'type', 'description', 'properties', 'required', 'items', 'enum', 'nullable',
    'format', 'minimum', 'maximum', 'minItems', 'maxItems', 'minLength', 'maxLength',
}

# JSON Schema estricto → el no-estricto que admite Gemini. La cota exacta
# (gt=0) la sigue validando pydantic en el servidor; al modelo le basta saber
# que el valor es positivo.
_RENOMBRAR = {'exclusiveMinimum': 'minimum', 'exclusiveMaximum': 'maximum'}


def _claves_sdk():
    """Claves (nombre o alias camelCase) que acepta google.genai.types.Schema."""
    try:
        from google.genai import types
    except ImportError:  # proveedor openai sin el SDK de Google instalado
        return None
    claves = set()
    for nombre, campo in types.Schema.model_fields.items():
        claves.add(nombre)
        if campo.alias:
            claves.add(campo.alias)
    return claves


@lru_cache(maxsize=1)
def _claves_validas():
    sdk = _claves_sdk()
    return _CLAVES_PERMITIDAS if sdk is None else _CLAVES_PERMITIDAS & sdk


def _elegir_variante(variantes):
    """anyOf con varias variantes (Decimal → [number, string]): Gemini no
    admite anyOf mezclado aquí; se prefiere la numérica, luego la primera."""
    for v in variantes:
        if v.get('type') in ('number', 'integer'):
            return v
    return variantes[0] if variantes else {'type': 'string'}


def _resolver(nodo, defs):
    """Inline de $ref y limpieza recursiva."""
    if isinstance(nodo, list):
        return [_resolver(n, defs) for n in nodo]
    if not isinstance(nodo, dict):
        return nodo
    if '$ref' in nodo:
        ref = nodo['$ref'].split('/')[-1]
        destino = copy.deepcopy(defs[ref])
        # description del campo gana sobre la del modelo referenciado
        if nodo.get('description'):
            destino['description'] = nodo['description']
        return _resolver(destino, defs)
    # Optional[X] → anyOf [X, {type: null}]  →  X + nullable
    if 'anyOf' in nodo:
        variantes = [v for v in nodo['anyOf'] if v.get('type') != 'null']
        es_nullable = len(variantes) < len(nodo['anyOf'])
        base = _resolver(_elegir_variante(variantes), defs)
        if nodo.get('description'):
            base['description'] = nodo['description']
        if es_nullable:
            base['nullable'] = True
        return base
    validas = _claves_validas()
    salida = {}
    for k, v in nodo.items():
        k = _RENOMBRAR.get(k, k)
        if k == 'properties':
            # las claves de properties son NOMBRES de campos: no se filtran
            salida['properties'] = {pk: _resolver(pv, defs) for pk, pv in v.items()}
        elif k == 'items':
            salida['items'] = _resolver(v, defs)
        elif k in validas:
            # si vinieran minimum y exclusiveMinimum a la vez se conserva el
            # primero (pydantic no emite ambos para un mismo campo)
            salida.setdefault(k, v)
        # title, default, $defs, pattern, additionalProperties… se descartan
    if salida.get('type') == 'object' and 'properties' not in salida:
        salida['properties'] = {}
    return salida


def schema_de_pydantic(modelo: Type[BaseModel]) -> dict:
    bruto = modelo.model_json_schema()
    defs = bruto.pop('$defs', {}) or {}
    return _resolver(bruto, defs)


def tool_de_pydantic(modelo: Type[BaseModel], name: str, description: str, escritura: bool = False) -> ToolSpec:
    return ToolSpec(name=name, description=description, parameters=schema_de_pydantic(modelo), escritura=escritura)
