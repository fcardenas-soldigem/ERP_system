from typing import List, Optional, Dict, Any
import logging
import requests
from django.conf import settings
from django.core.cache import cache
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentoService:
    """
    Servicio para consultar documentos de identidad usando la API de apis.net.pe
    Basado en la documentación oficial de apis.net.pe
    """
    
    def __init__(self, token: str = None) -> None:
        self._api_token = token or settings.APIS_NET_PE_TOKEN
        self._api_url = "https://api.apis.net.pe"

    def _get(self, path: str, params: dict) -> Optional[dict]:
        """
        Método privado para realizar peticiones GET a la API
        """
        url = f"{self._api_url}{path}"
        
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Referer": "django-erp-system",
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 422:
                logger.warning(f"{response.url} - Parámetros inválidos", extra={"params": params})
                logger.warning(response.text)
            elif response.status_code == 403:
                logger.warning(f"{response.url} - IP bloqueada")
            elif response.status_code == 429:
                logger.warning(f"{response.url} - Demasiadas consultas, agregar delay")
            elif response.status_code == 401:
                logger.warning(f"{response.url} - Token inválido o limitado")
            else:
                logger.warning(f"{response.url} - Error del servidor status_code={response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con {url}: {str(e)}")
            
        return None

    def get_person(self, dni: str) -> Optional[dict]:
        """
        Consulta datos de una persona por DNI en RENIEC
        
        Args:
            dni (str): Número de DNI (8 dígitos)
            
        Returns:
            dict: Datos de la persona o None si hay error
        """
        # Usar endpoint v1 (compatible con el token/plan actual)
        return self._get("/v1/dni", {"numero": dni})

    def get_company(self, ruc: str) -> Optional[dict]:
        """
        Consulta datos de una empresa por RUC en SUNAT
        
        Args:
            ruc (str): Número de RUC (11 dígitos)
            
        Returns:
            dict: Datos de la empresa o None si hay error
        """
        # Usar endpoint v1 (compatible con el token/plan actual)
        return self._get("/v1/ruc", {"numero": ruc})

    def get_exchange_rate(self, date: str) -> Optional[dict]:
        """
        Consulta tipo de cambio del SBS para una fecha específica
        
        Args:
            date (str): Fecha en formato YYYY-MM-DD
            
        Returns:
            dict: Tipo de cambio o None si hay error
        """
        return self._get("/v2/sbs/tipo-cambio", {"date": date})

    def get_exchange_rate_today(self) -> Optional[dict]:
        """
        Consulta tipo de cambio del SBS del día actual
        
        Returns:
            dict: Tipo de cambio del día o None si hay error
        """
        return self._get("/v2/sbs/tipo-cambio", {})

    def get_exchange_rate_for_month(self, month: int, year: int) -> Optional[List[dict]]:
        """
        Consulta tipo de cambio del SBS de un mes específico
        
        Args:
            month (int): Mes (1-12)
            year (int): Año
            
        Returns:
            List[dict]: Lista de tipos de cambio del mes o None si hay error
        """
        return self._get("/v2/sbs/tipo-cambio", {"month": month, "year": year})

    @classmethod
    def consultar_dni(cls, dni: str) -> Dict[str, Any]:
        """
        Consulta datos de una persona por DNI con cache y formateo
        
        Args:
            dni (str): Número de DNI (8 dígitos)
            
        Returns:
            dict: Datos formateados de la persona o mensaje de error
        """
        # Validar formato de DNI
        if not dni or len(dni) != 8 or not dni.isdigit():
            return {
                "success": False,
                "error": "DNI inválido. Debe tener 8 dígitos numéricos."
            }

        # Verificar cache primero
        cache_key = f"dni_{dni}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"DNI {dni} encontrado en cache")
            return cached_data

        # Realizar consulta
        service = cls()
        data = service.get_person(dni)
        
        if data:
            # Formatear respuesta exitosa
            result = {
                "success": True,
                "data": {
                    "nombres": data.get("nombres", ""),
                    "apellido_paterno": data.get("apellidoPaterno", ""),
                    "apellido_materno": data.get("apellidoMaterno", ""),
                    "numero_documento": data.get("numeroDocumento", dni),
                    "nombre_completo": f"{data.get('nombres', '')} {data.get('apellidoPaterno', '')} {data.get('apellidoMaterno', '')}".strip()
                }
            }
            
            # Guardar en cache por 1 hora
            cache.set(cache_key, result, 3600)
            logger.info(f"DNI {dni} consultado exitosamente")
            return result
        else:
            # Error en la consulta
            logger.error(f"Error consultando DNI {dni}")
            return {
                "success": False,
                "error": "No se pudo consultar el DNI. Verifique el número o intente más tarde."
            }

    @classmethod
    def consultar_ruc(cls, ruc: str) -> Dict[str, Any]:
        """
        Consulta datos de una empresa por RUC con cache y formateo
        
        Args:
            ruc (str): Número de RUC (11 dígitos)
            
        Returns:
            dict: Datos formateados de la empresa o mensaje de error
        """
        # Validar formato de RUC
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            return {
                "success": False,
                "error": "RUC inválido. Debe tener 11 dígitos numéricos."
            }

        # Verificar cache primero
        cache_key = f"ruc_{ruc}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"RUC {ruc} encontrado en cache")
            return cached_data

        # Realizar consulta
        service = cls()
        data = service.get_company(ruc)
        
        if data:
            # Formatear respuesta exitosa
            result = {
                "success": True,
                "data": {
                    "ruc": data.get("numeroDocumento", ruc),
                    "razon_social": data.get("razonSocial", ""),
                    "nombre_comercial": data.get("nombreComercial", ""),
                    "estado": data.get("estado", ""),
                    "condicion": data.get("condicion", ""),
                    "direccion": data.get("direccion", ""),
                    "ubigeo": data.get("ubigeo", ""),
                    "via_tipo": data.get("viaTipo", ""),
                    "via_nombre": data.get("viaNombre", ""),
                    "zona_rural": data.get("zonaRural", ""),
                    "zona_tipo": data.get("zonaTipo", ""),
                    "numero": data.get("numero", ""),
                    "interior": data.get("interior", ""),
                    "lote": data.get("lote", ""),
                    "departamento": data.get("departamento", ""),
                    "manzana": data.get("manzana", ""),
                    "kilometro": data.get("kilometro", "")
                }
            }
            
            # Guardar en cache por 1 hora
            cache.set(cache_key, result, 3600)
            logger.info(f"RUC {ruc} consultado exitosamente")
            return result
        else:
            # Error en la consulta
            logger.error(f"Error consultando RUC {ruc}")
            return {
                "success": False,
                "error": "No se pudo consultar el RUC. Verifique el número o intente más tarde."
            }

    @classmethod
    def consultar_documento(cls, numero_documento: str, tipo_documento: str) -> Dict[str, Any]:
        """
        Consulta un documento según su tipo
        
        Args:
            numero_documento (str): Número del documento
            tipo_documento (str): 'dni' o 'ruc'
            
        Returns:
            dict: Datos del documento o mensaje de error
        """
        if tipo_documento.lower() == 'dni':
            return cls.consultar_dni(numero_documento)
        elif tipo_documento.lower() == 'ruc':
            return cls.consultar_ruc(numero_documento)
        else:
            return {
                "success": False,
                "error": "Tipo de documento no válido. Use 'dni' o 'ruc'."
            }

    @classmethod
    def consultar_tipo_cambio(cls, fecha: str = None) -> Dict[str, Any]:
        """
        Consulta el tipo de cambio del SBS (Superintendencia de Banca, Seguros y AFP)
        
        Args:
            fecha (str, optional): Fecha en formato YYYY-MM-DD. Si no se proporciona, usa la fecha actual.
            
        Returns:
            dict: Tipo de cambio o mensaje de error
        """
        cache_key = f"tipo_cambio_{fecha or 'hoy'}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Tipo de cambio {fecha or 'de hoy'} encontrado en cache")
            return cached_data

        service = cls()
        
        if fecha:
            data = service.get_exchange_rate(fecha)
        else:
            data = service.get_exchange_rate_today()
        
        if data:
            result = {
                "success": True,
                "data": {
                    "fecha": data.get("fecha", ""),
                    "compra": data.get("precioCompra", 0),
                    "venta": data.get("precioVenta", 0),
                    "moneda": data.get("moneda", "USD"),
                    "origen": "SBS"
                }
            }
            
            # Guardar en cache por 30 minutos
            cache.set(cache_key, result, 1800)
            logger.info(f"Tipo de cambio {fecha or 'de hoy'} consultado exitosamente")
            return result
        else:
            logger.error(f"Error consultando tipo de cambio {fecha or 'de hoy'}")
            return {
                "success": False,
                "error": "No se pudo consultar el tipo de cambio. Intente más tarde."
            }

    @classmethod
    def consultar_tipo_cambio_mes(cls, mes: int, año: int) -> Dict[str, Any]:
        """
        Consulta los tipos de cambio de un mes específico
        
        Args:
            mes (int): Mes (1-12)
            año (int): Año
            
        Returns:
            dict: Lista de tipos de cambio del mes o mensaje de error
        """
        if not (1 <= mes <= 12):
            return {
                "success": False,
                "error": "El mes debe estar entre 1 y 12."
            }

        cache_key = f"tipo_cambio_mes_{mes}_{año}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Tipos de cambio del mes {mes}/{año} encontrados en cache")
            return cached_data

        service = cls()
        data = service.get_exchange_rate_for_month(mes, año)
        
        if data and isinstance(data, list):
            result = {
                "success": True,
                "data": [
                    {
                        "fecha": item.get("fecha", ""),
                        "compra": item.get("precioCompra", 0),
                        "venta": item.get("precioVenta", 0),
                        "moneda": item.get("moneda", "USD"),
                        "origen": "SBS"
                    }
                    for item in data
                ]
            }
            
            # Guardar en cache por 2 horas
            cache.set(cache_key, result, 7200)
            logger.info(f"Tipos de cambio del mes {mes}/{año} consultados exitosamente")
            return result
        else:
            logger.error(f"Error consultando tipos de cambio del mes {mes}/{año}")
            return {
                "success": False,
                "error": "No se pudo consultar los tipos de cambio del mes. Intente más tarde."
            } 