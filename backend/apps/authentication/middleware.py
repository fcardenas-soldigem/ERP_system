from django.db import connection
from django.conf import settings
from django.db.utils import OperationalError

class DatabaseRouterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            db_name = f"user_{request.user.id}_db"
            try:
                # Intentar cambiar la base de datos
                settings.DATABASES['default']['NAME'] = db_name
                # Verificar si la base de datos existe
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                # Si la base de datos no existe, manejar el error
                # Por ejemplo, redirigir a una página de error o usar la base de datos predeterminada
                settings.DATABASES['default']['NAME'] = 'ERP_system'  # Volver a la base de datos predeterminada
        return self.get_response(request) 