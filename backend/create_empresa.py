from core.models import Empresa

if not Empresa.objects.exists():
    Empresa.objects.create(
        ruc='12345678901',
        razon_social='Empresa Ejemplo',
        nombre_comercial='Ejemplo',
        direccion='Dirección de Ejemplo',
        telefono='123456789',
        email='ejemplo@empresa.com'
    )
