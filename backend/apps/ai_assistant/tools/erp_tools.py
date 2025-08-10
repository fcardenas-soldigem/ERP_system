from openai.lib import pydantic_function_tool
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from decimal import Decimal

class ProductoVenta(BaseModel):
    """Producto a vender"""
    producto_sku: str = Field(..., description="SKU del producto a vender (código único del producto)")
    cantidad: int = Field(..., description="Cantidad a vender", gt=0)
    precio_unitario: float = Field(..., description="Precio unitario de venta", gt=0)

class CrearVentaParams(BaseModel):
    """Parámetros para crear una venta en el sistema ERP"""
    cliente_id: int = Field(..., description="ID del cliente que realiza la compra")
    tipo_venta: Literal["contado", "credito_30", "credito_60"] = Field(..., description="Tipo de venta: contado (pago inmediato), credito_30 (crédito a 30 días), credito_60 (crédito a 60 días)")
    metodo_pago: Literal["efectivo", "transferencia", "cheque", "tarjeta"] = Field(..., description="Método de pago: efectivo, transferencia bancaria, cheque o tarjeta")
    productos: List[ProductoVenta] = Field(..., description="Lista de productos a vender con sus cantidades y precios")
    igv_incluido: bool = Field(default=True, description="Si los precios incluyen IGV (18%) o no")
    notas: Optional[str] = Field(None, description="Notas adicionales sobre la venta")

class ProductoCompra(BaseModel):
    """Producto a comprar"""
    producto_sku: str = Field(..., description="SKU del producto a comprar (código único del producto)")
    cantidad: int = Field(..., description="Cantidad a comprar", gt=0)
    precio_unitario: float = Field(..., description="Precio unitario de compra", gt=0)

class CrearCompraParams(BaseModel):
    """Parámetros para crear una compra en el sistema ERP"""
    proveedor_id: int = Field(..., description="ID del proveedor de quien se compra")
    almacen_id: int = Field(..., description="ID del almacén donde se almacenarán los productos")
    tipo_compra: Literal["contado", "credito_30", "credito_60"] = Field(..., description="Tipo de compra: contado (pago inmediato), credito_30 (crédito a 30 días), credito_60 (crédito a 60 días)")
    productos: List[ProductoCompra] = Field(..., description="Lista de productos a comprar con sus cantidades y precios")
    igv_incluido: bool = Field(default=True, description="Si los precios incluyen IGV (18%) o no")
    metodo_pago: Literal["efectivo", "transferencia", "cheque", "tarjeta"] = Field(default="transferencia", description="Método de pago para la compra")
    notas: Optional[str] = Field(None, description="Notas adicionales sobre la compra")

class BuscarProductosParams(BaseModel):
    """Parámetros para buscar productos en el inventario"""
    termino_busqueda: str = Field(..., description="Término de búsqueda (nombre, descripción, o SKU del producto)")
    limite: int = Field(default=10, description="Límite de resultados a retornar", le=50)

class BuscarClientesParams(BaseModel):
    """Parámetros para buscar clientes"""
    termino_busqueda: str = Field(..., description="Término de búsqueda (nombre, documento o parte del nombre del cliente)")
    limite: int = Field(default=10, description="Límite de resultados a retornar", le=50)

# Definir las tools para OpenAI usando la nueva API
CREAR_VENTA_TOOL = pydantic_function_tool(
    CrearVentaParams,
    name="crear_venta",
    description="""Crear una nueva venta en el sistema ERP. 

CAMPOS OBLIGATORIOS:
- cliente_id: ID numérico del cliente (usar buscar_productos si no conoces el ID)
- productos: Lista con SKU, cantidad y precio de cada producto
- tipo_venta: 'contado', 'credito_30' o 'credito_60'
- metodo_pago: 'efectivo', 'transferencia', 'cheque' o 'tarjeta'

IMPORTANTE: Siempre solicita al usuario TODOS los campos necesarios antes de crear la venta."""
)

CREAR_COMPRA_TOOL = pydantic_function_tool(
    CrearCompraParams,
    name="crear_compra", 
    description="Crear una nueva compra en el sistema ERP. Esta función registra una compra a proveedores, calcula totales con IGV, actualiza el inventario aumentando el stock de los productos comprados y genera el registro correspondiente."
)

BUSCAR_PRODUCTOS_TOOL = pydantic_function_tool(
    BuscarProductosParams,
    name="buscar_productos",
    description="Buscar productos en el inventario por nombre, descripción o SKU. Útil para encontrar el SKU correcto de un producto antes de crear ventas o compras, o para verificar stock disponible."
)

BUSCAR_CLIENTES_TOOL = pydantic_function_tool(
    BuscarClientesParams,
    name="buscar_clientes",
    description="Buscar clientes por nombre o documento. Útil para encontrar el ID del cliente antes de crear ventas. Devuelve ID, nombre y documento de los clientes encontrados."
)

# Lista de todas las tools disponibles para el asistente
ERP_TOOLS = [CREAR_VENTA_TOOL, CREAR_COMPRA_TOOL, BUSCAR_PRODUCTOS_TOOL, BUSCAR_CLIENTES_TOOL] 