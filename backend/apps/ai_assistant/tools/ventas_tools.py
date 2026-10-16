from typing import List, Optional
from pydantic import BaseModel, Field

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

# Las ToolSpec (nombre, descripción, schema) se construyen en services/perfiles.py
# a partir de estos modelos pydantic, independientes del proveedor de LLM.
