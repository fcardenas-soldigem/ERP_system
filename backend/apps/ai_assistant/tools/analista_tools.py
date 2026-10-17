from typing import List, Optional
from pydantic import BaseModel, Field

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

# Las ToolSpec (nombre, descripción, schema) se construyen en services/perfiles.py
# a partir de estos modelos pydantic, independientes del proveedor de LLM.
