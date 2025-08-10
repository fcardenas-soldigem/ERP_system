from typing import List, Optional
from pydantic import BaseModel, Field
from openai import pydantic_function_tool

class ProductoVentaParams(BaseModel):
    producto_sku: str = Field(description="SKU del producto a vender")
    cantidad: int = Field(description="Cantidad a vender")
    precio_unitario: float = Field(description="Precio unitario del producto")

class CrearVentaParams(BaseModel):
    cliente_id: int = Field(description="ID del cliente")
    tipo_venta: str = Field(description="Tipo de venta: 'contado' o 'credito'")
    metodo_pago: str = Field(description="Método de pago: 'efectivo', 'transferencia', 'tarjeta', 'cheque'")
    productos: List[ProductoVentaParams] = Field(description="Lista de productos a vender")
    igv_incluido: bool = Field(default=True, description="Si el IGV está incluido en los precios")
    notas: Optional[str] = Field(default="", description="Notas adicionales para la venta")

class BuscarProductosParams(BaseModel):
    query: str = Field(description="Término de búsqueda para productos (nombre, descripción o SKU)")

class BuscarClientesParams(BaseModel):
    query: str = Field(description="Término de búsqueda para clientes (nombre o documento)")

# Tools específicos para ventas
CREAR_VENTA_TOOL = pydantic_function_tool(CrearVentaParams, name="crear_venta", description="Crear una nueva venta con productos específicos. Todos los campos son obligatorios: cliente_id, tipo_venta, metodo_pago, productos (con producto_sku, cantidad, precio_unitario)")

BUSCAR_PRODUCTOS_TOOL = pydantic_function_tool(BuscarProductosParams, name="buscar_productos", description="Buscar productos disponibles por nombre, descripción o SKU")

BUSCAR_CLIENTES_TOOL = pydantic_function_tool(BuscarClientesParams, name="buscar_clientes", description="Buscar clientes por nombre o documento para obtener su ID")

# Lista de herramientas para el asistente de ventas
VENTAS_TOOLS = [
    CREAR_VENTA_TOOL,
    BUSCAR_PRODUCTOS_TOOL,
    BUSCAR_CLIENTES_TOOL
] 