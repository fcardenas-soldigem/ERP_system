from typing import List, Optional
from pydantic import BaseModel, Field

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

# Las ToolSpec (nombre, descripción, schema) se construyen en services/perfiles.py
# a partir de estos modelos pydantic, independientes del proveedor de LLM.
