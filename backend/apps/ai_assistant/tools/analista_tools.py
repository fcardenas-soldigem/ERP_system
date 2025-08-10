from typing import List, Optional
from pydantic import BaseModel, Field
from openai import pydantic_function_tool

class AnalisisVentasParams(BaseModel):
    periodo: str = Field(description="Período para análisis: 'semana', 'mes', 'trimestre', 'año'")
    fecha_inicio: Optional[str] = Field(default=None, description="Fecha de inicio (YYYY-MM-DD)")
    fecha_fin: Optional[str] = Field(default=None, description="Fecha de fin (YYYY-MM-DD)")

class AnalisisInventarioParams(BaseModel):
    categoria: Optional[str] = Field(default=None, description="Categoría específica a analizar")
    stock_minimo: Optional[int] = Field(default=None, description="Filtrar productos con stock menor a este valor")

class AnalisisClientesParams(BaseModel):
    periodo: str = Field(description="Período para análisis: 'semana', 'mes', 'trimestre', 'año'")
    top_clientes: Optional[int] = Field(default=10, description="Número de top clientes a mostrar")

class ConsultaLibreParams(BaseModel):
    consulta: str = Field(description="Consulta libre sobre datos comerciales")

# Tools específicos para análisis (sin crear ventas/compras)
ANALIZAR_VENTAS_TOOL = pydantic_function_tool(
    AnalisisVentasParams, 
    name="analizar_ventas", 
    description="Analizar performance de ventas en un período específico, tendencias y métricas clave"
)

ANALIZAR_INVENTARIO_TOOL = pydantic_function_tool(
    AnalisisInventarioParams, 
    name="analizar_inventario", 
    description="Analizar estado del inventario, productos con stock bajo, rotación de productos"
)

ANALIZAR_CLIENTES_TOOL = pydantic_function_tool(
    AnalisisClientesParams, 
    name="analizar_clientes", 
    description="Analizar comportamiento de clientes, top compradores, frecuencia de compra"
)

CONSULTA_LIBRE_TOOL = pydantic_function_tool(
    ConsultaLibreParams, 
    name="consulta_libre", 
    description="Responder consultas libres sobre datos comerciales, tendencias y oportunidades"
)

# Lista de herramientas para Jorge como analista comercial
ANALISTA_TOOLS = [
    ANALIZAR_VENTAS_TOOL,
    ANALIZAR_INVENTARIO_TOOL, 
    ANALIZAR_CLIENTES_TOOL,
    CONSULTA_LIBRE_TOOL
] 