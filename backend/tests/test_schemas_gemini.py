"""
Contrato de schemas con el SDK de Gemini (sin red).

Para CADA tool de CADA perfil —asistente web (jorge, ventas, compras; incluidas
las de escritura, aunque LLM_WRITE_TOOLS esté apagado) y el bot de canales— se
construye `google.genai.types.FunctionDeclaration` con el schema sanitizado.
`types.Schema` es pydantic con extra='forbid': cualquier clave no soportada
(exclusiveMinimum, $ref, pattern…) revienta aquí, en CI, y no contra Vertex.

Origen: eval_agente dio 0/15 contra Vertex real por
`parameters.properties.items.items.properties.cantidad.anyOf.0.exclusiveMinimum
— Extra inputs are not permitted`.
"""
import json
from decimal import Decimal
from typing import Optional

from django.test import SimpleTestCase
from google.genai import types
from pydantic import BaseModel, Field

from apps.ai_assistant.services.perfiles import PERFILES
from apps.ai_assistant.services.tool_specs import schema_de_pydantic
from apps.canales.nucleo.interprete import _tools as tools_canales


def _todas_las_tools():
    """[(origen, ToolSpec)] — todas, no solo las activas."""
    out = []
    for clave, perfil in PERFILES.items():
        for spec in perfil.tools:
            out.append((f'asistente:{clave}', spec))
    for spec in tools_canales():
        out.append(('canales', spec))
    return out


class SchemasGeminiTests(SimpleTestCase):
    def test_cada_tool_construye_function_declaration(self):
        tools = _todas_las_tools()
        self.assertGreater(len(tools), 8, 'no se encontraron tools: ¿cambió el registro?')
        fallos = []
        for origen, spec in tools:
            try:
                types.FunctionDeclaration(
                    name=spec.name, description=spec.description, parameters=spec.parameters,
                )
            except Exception as e:  # pydantic.ValidationError del SDK
                fallos.append(f'{origen}/{spec.name}: {str(e).splitlines()[0:3]}')
        self.assertEqual(fallos, [], 'schemas que Gemini rechazaría:\n' + '\n'.join(fallos))

    def test_cubre_los_tres_perfiles_web_y_el_bot(self):
        origenes = {o for o, _ in _todas_las_tools()}
        self.assertEqual(origenes, {'asistente:jorge', 'asistente:ventas', 'asistente:compras', 'canales'})

    def test_ninguna_clave_prohibida_sobrevive(self):
        prohibidas = ('exclusiveMinimum', 'exclusiveMaximum', '$ref', '$defs', '"title"', '"default"', 'anyOf')
        for origen, spec in _todas_las_tools():
            plano = json.dumps(spec.parameters)
            for clave in prohibidas:
                self.assertNotIn(clave, plano, f'{origen}/{spec.name} conserva {clave}')


class SanitizadorTests(SimpleTestCase):
    """Comportamiento puntual del sanitizador central."""

    class Ejemplo(BaseModel):
        cantidad: Decimal = Field(gt=0, le=Decimal('100'))
        monto: Optional[Decimal] = Field(default=None, gt=0)
        tope: int = Field(lt=10)
        nombre: str = Field(min_length=2, pattern=r'^[a-z]+$')

    def test_exclusive_se_convierte_en_minimum_maximum(self):
        props = schema_de_pydantic(self.Ejemplo)['properties']
        self.assertEqual(props['cantidad']['minimum'], 0)
        self.assertEqual(props['cantidad']['maximum'], 100)
        self.assertEqual(props['tope']['maximum'], 10)
        self.assertNotIn('exclusiveMinimum', json.dumps(props))

    def test_decimal_prefiere_number_y_optional_queda_nullable(self):
        props = schema_de_pydantic(self.Ejemplo)['properties']
        self.assertEqual(props['cantidad']['type'], 'number')   # antes colapsaba a string
        self.assertEqual(props['monto']['type'], 'number')
        self.assertTrue(props['monto']['nullable'])

    def test_claves_no_soportadas_se_descartan(self):
        props = schema_de_pydantic(self.Ejemplo)['properties']
        self.assertEqual(props['nombre']['minLength'], 2)
        self.assertNotIn('pattern', props['nombre'])
        types.FunctionDeclaration(name='x', parameters=schema_de_pydantic(self.Ejemplo))

    def test_la_validacion_real_sigue_en_pydantic(self):
        """El schema afloja gt→minimum para Gemini, pero el servidor rechaza 0."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.Ejemplo(cantidad=0, tope=1, nombre='ab')
