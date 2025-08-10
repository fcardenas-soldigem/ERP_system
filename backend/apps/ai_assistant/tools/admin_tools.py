from typing import List, Optional
from pydantic import BaseModel, Field
from openai import pydantic_function_tool

class DirigirAgenteParams(BaseModel):
    agente_recomendado: str = Field(description="Agente recomendado: 'jorge', 'ventas', 'compras'")
    razon: str = Field(description="Razón por la cual se recomienda este agente")
    mensaje_usuario: str = Field(description="Mensaje original del usuario")

class ResumenEjecutivoParams(BaseModel):
    tipo_resumen: str = Field(description="Tipo de resumen: 'general', 'ventas', 'compras', 'inventario'")
    periodo: Optional[str] = Field(default="mes", description="Período para el resumen: 'semana', 'mes', 'trimestre'")

class ConsultaGeneralParams(BaseModel):
    consulta: str = Field(description="Consulta general sobre el sistema ERP")
    requiere_datos: bool = Field(description="Si requiere acceso a datos específicos")

# Tools específicos para el administrador
DIRIGIR_AGENTE_TOOL = pydantic_function_tool(
    DirigirAgenteParams, 
    name="dirigir_agente", 
    description="Recomendar el agente más apropiado según la necesidad del usuario"
)

RESUMEN_EJECUTIVO_TOOL = pydantic_function_tool(
    ResumenEjecutivoParams, 
    name="resumen_ejecutivo", 
    description="Generar resumen ejecutivo del estado del negocio"
)

CONSULTA_GENERAL_TOOL = pydantic_function_tool(
    ConsultaGeneralParams, 
    name="consulta_general", 
    description="Responder consultas generales sobre el sistema ERP"
)

# Lista de herramientas para el administrador
ADMIN_TOOLS = [
    DIRIGIR_AGENTE_TOOL,
    RESUMEN_EJECUTIVO_TOOL,
    CONSULTA_GENERAL_TOOL
] 