"""
Utilidades de cache para optimizar el rendimiento del ERP.
"""
from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json


def get_cache_timeout(cache_type):
    """Obtiene el timeout configurado para un tipo de cache específico."""
    timeouts = getattr(settings, 'CACHE_TIMEOUTS', {})
    return timeouts.get(cache_type, 300)  # 5 minutos por defecto


def make_cache_key(prefix, *args, **kwargs):
    """
    Genera una clave de cache única basada en el prefijo y argumentos.
    """
    key_parts = [prefix]
    
    # Agregar argumentos posicionales
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    # Agregar argumentos con nombre (ordenados para consistencia)
    for key in sorted(kwargs.keys()):
        if kwargs[key] is not None:
            key_parts.append(f"{key}:{kwargs[key]}")
    
    key_string = ':'.join(key_parts)
    
    # Si la clave es muy larga, usar hash
    if len(key_string) > 200:
        hash_suffix = hashlib.md5(key_string.encode()).hexdigest()[:12]
        key_string = f"{prefix}:{hash_suffix}"
    
    return key_string


def cache_result(cache_type, timeout=None, key_prefix=None):
    """
    Decorador para cachear el resultado de una función.
    
    Uso:
        @cache_result('productos', timeout=120)
        def get_productos(empresa_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determinar el timeout
            cache_timeout = timeout or get_cache_timeout(cache_type)
            
            # Generar clave de cache
            prefix = key_prefix or f"{cache_type}:{func.__name__}"
            cache_key = make_cache_key(prefix, *args, **kwargs)
            
            # Intentar obtener del cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache.set(cache_key, result, cache_timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """
    Invalida todas las claves de cache que coincidan con el patrón.
    
    Nota: Solo funciona con backends que soporten delete_pattern (como Redis).
    Para LocMemCache, se usa un enfoque más simple.
    """
    try:
        # Intentar usar delete_pattern si está disponible (Redis)
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(f"*{pattern}*")
        else:
            # Para cache en memoria, limpiar claves específicas
            cache.clear()
    except Exception:
        # Fallback: limpiar todo el cache
        cache.clear()


def invalidate_empresa_cache(empresa_id, cache_types=None):
    """
    Invalida el cache relacionado con una empresa específica.
    
    Args:
        empresa_id: ID de la empresa
        cache_types: Lista de tipos de cache a invalidar (ej: ['productos', 'inventario_mp'])
    """
    if cache_types is None:
        cache_types = ['productos', 'inventario_mp', 'inventario_pt', 'resumen', 'alertas']
    
    for cache_type in cache_types:
        key_pattern = f"{cache_type}:*:{empresa_id}"
        invalidate_cache(key_pattern)


class CacheManager:
    """
    Gestor de cache para el ERP con métodos específicos por entidad.
    """
    
    @staticmethod
    def get_productos(empresa_id, force_refresh=False):
        """Obtiene productos cacheados o los carga."""
        cache_key = make_cache_key('productos', empresa_id)
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        return None  # El caller debe cargar y cachear
    
    @staticmethod
    def set_productos(empresa_id, data):
        """Cachea la lista de productos."""
        cache_key = make_cache_key('productos', empresa_id)
        cache.set(cache_key, data, get_cache_timeout('productos'))
    
    @staticmethod
    def invalidate_productos(empresa_id):
        """Invalida el cache de productos de una empresa."""
        cache_key = make_cache_key('productos', empresa_id)
        cache.delete(cache_key)
    
    @staticmethod
    def get_inventario_mp(empresa_id, almacen_id=None, force_refresh=False):
        """Obtiene inventario de materias primas cacheado."""
        cache_key = make_cache_key('inventario_mp', empresa_id, almacen=almacen_id)
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        return None
    
    @staticmethod
    def set_inventario_mp(empresa_id, data, almacen_id=None):
        """Cachea inventario de materias primas."""
        cache_key = make_cache_key('inventario_mp', empresa_id, almacen=almacen_id)
        cache.set(cache_key, data, get_cache_timeout('inventario_mp'))
    
    @staticmethod
    def invalidate_inventario_mp(empresa_id):
        """Invalida cache de inventario de materias primas."""
        invalidate_cache(f'inventario_mp:*:{empresa_id}')
    
    @staticmethod
    def get_inventario_pt(empresa_id, almacen_id=None, force_refresh=False):
        """Obtiene inventario de productos terminados cacheado."""
        cache_key = make_cache_key('inventario_pt', empresa_id, almacen=almacen_id)
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        return None
    
    @staticmethod
    def set_inventario_pt(empresa_id, data, almacen_id=None):
        """Cachea inventario de productos terminados."""
        cache_key = make_cache_key('inventario_pt', empresa_id, almacen=almacen_id)
        cache.set(cache_key, data, get_cache_timeout('inventario_pt'))
    
    @staticmethod
    def invalidate_inventario_pt(empresa_id):
        """Invalida cache de inventario de productos terminados."""
        invalidate_cache(f'inventario_pt:*:{empresa_id}')
    
    @staticmethod
    def get_alertas(empresa_id, tipo=None, force_refresh=False):
        """Obtiene alertas cacheadas."""
        cache_key = make_cache_key('alertas', empresa_id, tipo=tipo)
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        return None
    
    @staticmethod
    def set_alertas(empresa_id, data, tipo=None):
        """Cachea alertas."""
        cache_key = make_cache_key('alertas', empresa_id, tipo=tipo)
        cache.set(cache_key, data, get_cache_timeout('alertas'))
    
    @staticmethod
    def invalidate_all_empresa(empresa_id):
        """Invalida todo el cache de una empresa."""
        invalidate_empresa_cache(empresa_id)


# Singleton para acceso fácil
cache_manager = CacheManager()
