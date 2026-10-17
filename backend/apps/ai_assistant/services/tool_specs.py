"""
Conversión de modelos pydantic → `ToolSpec` con un JSON Schema que aceptan tanto
Gemini (function declarations, subconjunto OpenAPI 3.0: SIN $ref/$defs, SIN title,
SIN default; `anyOf [X, null]` → `nullable`) como la API `chat.completions`.

Antes se usaba `openai.pydantic_function_tool`, que ata la definición a un
proveedor. Las clases pydantic de `tools/*.py` siguen siendo la fuente de verdad.
"""
from __future__ import annotations

import copy
from typing import Type

from pydantic import BaseModel

from .llm_client import ToolSpec

_CLAVES_PERMITIDAS = {
    'type', 'description', 'properties', 'required', 'items', 'enum', 'nullable',
    'format', 'minimum', 'maximum', 'minItems', 'maxItems', 'minLength', 'maxLength',
}


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
        base = _resolver(variantes[0], defs) if len(variantes) == 1 else {'type': 'string'}
        if nodo.get('description'):
            base['description'] = nodo['description']
        if es_nullable:
            base['nullable'] = True
        return base
    salida = {}
    for k, v in nodo.items():
        if k == 'properties':
            salida['properties'] = {pk: _resolver(pv, defs) for pk, pv in v.items()}
        elif k == 'items':
            salida['items'] = _resolver(v, defs)
        elif k in _CLAVES_PERMITIDAS:
            salida[k] = v
        # title, default, $defs, exclusiveMinimum, additionalProperties… se descartan
    if salida.get('type') == 'object' and 'properties' not in salida:
        salida['properties'] = {}
    return salida


def schema_de_pydantic(modelo: Type[BaseModel]) -> dict:
    bruto = modelo.model_json_schema()
    defs = bruto.pop('$defs', {}) or {}
    return _resolver(bruto, defs)


def tool_de_pydantic(modelo: Type[BaseModel], name: str, description: str, escritura: bool = False) -> ToolSpec:
    return ToolSpec(name=name, description=description, parameters=schema_de_pydantic(modelo), escritura=escritura)
