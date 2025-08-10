from typing import List, Optional
from pydantic import BaseModel, Field
from openai import pydantic_function_tool

class ProductoCompraParams(BaseModel):
    producto_sku: str = Field(description="SKU del producto a comprar")
    cantidad: int = Field(description="Cantidad a comprar")
    precio_unitario: float = Field(description="Precio unitario de compra")

class CrearCompraParams(BaseModel):
    proveedor_id: int = Field(description="ID del proveedor")
    almacen_id: int = Field(description="ID del almacén donde se recibirán los productos")
    tipo_compra: str = Field(description="Tipo de compra: 'contado' o 'credito'")
    metodo_pago: str = Field(description="Método de pago: 'efectivo', 'transferencia', 'tarjeta', 'cheque'")
    productos: List[ProductoCompraParams] = Field(description="Lista de productos a comprar")
    fecha_entrega: Optional[str] = Field(default=None, description="Fecha esperada de entrega (YYYY-MM-DD)")
    notas: Optional[str] = Field(default="", description="Notas adicionales para la compra")

class BuscarProveedoresParams(BaseModel):
    query: str = Field(description="Término de búsqueda para proveedores (razón social o RUC)")

class BuscarProductosComprasParams(BaseModel):
    query: str = Field(description="Término de búsqueda para productos (nombre, descripción o SKU)")

class BuscarAlmacenesParams(BaseModel):
    query: str = Field(description="Término de búsqueda para almacenes (nombre o dirección)")

# Tools específicos para compras
CREAR_COMPRA_TOOL = pydantic_function_tool(
    CrearCompraParams, 
    name="crear_compra", 
    description="Crear una nueva orden de compra con productos específicos. Todos los campos son obligatorios: proveedor_id, almacen_id, tipo_compra, metodo_pago, productos (con producto_sku, cantidad, precio_unitario)"
)

BUSCAR_PRODUCTOS_COMPRAS_TOOL = pydantic_function_tool(
    BuscarProductosComprasParams, 
    name="buscar_productos", 
    description="Buscar productos disponibles para compra por nombre, descripción o SKU"
)

BUSCAR_PROVEEDORES_TOOL = pydantic_function_tool(
    BuscarProveedoresParams, 
    name="buscar_proveedores", 
    description="Buscar proveedores por razón social o RUC para obtener su ID"
)

BUSCAR_ALMACENES_TOOL = pydantic_function_tool(
    BuscarAlmacenesParams, 
    name="buscar_almacenes", 
    description="Buscar almacenes disponibles por nombre o dirección para obtener su ID"
)

# Lista de herramientas para el asistente de compras
COMPRAS_TOOLS = [
    CREAR_COMPRA_TOOL,
    BUSCAR_PRODUCTOS_COMPRAS_TOOL,
    BUSCAR_PROVEEDORES_TOOL,
    BUSCAR_ALMACENES_TOOL
] 