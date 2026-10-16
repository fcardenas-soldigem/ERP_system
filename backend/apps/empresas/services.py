"""
Alta de un tenant nuevo (empresa + usuario administrador) en una sola transacción.

Es el flujo que seguirá cada empresa nueva: NO hay endpoint público de registro
(decisión de AUDITORIA_AISLAMIENTO_TENANTS: no abrir el registro a terceros); el alta
la hace la plataforma con `python manage.py crear_tenant` o llamando a este servicio.

Garantías:
- `ruc` y `email` únicos (ValidationError legible si chocan).
- El usuario queda ligado a SU empresa con rol admin; nunca is_superuser (eso es solo
  para la plataforma; ver apps.core.admin / M3).
- La numeración de documentos (COT, V, OC, OCS) es POR EMPRESA, así que el tenant
  nuevo arranca en 1 sin chocar con los existentes (ver apps.core.numbering).
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Empresa


@transaction.atomic
def registrar_empresa(*, nombre, ruc, admin_email, admin_password, admin_nombre,
                      admin_apellido, modo_inventario='con_stock', **datos_empresa):
    """Crea la empresa y su primer usuario (admin). Devuelve (empresa, usuario)."""
    User = get_user_model()
    nombre = (nombre or '').strip()
    ruc = (ruc or '').strip()
    admin_email = (admin_email or '').strip().lower()
    if not nombre:
        raise ValidationError({'nombre': 'El nombre de la empresa es obligatorio.'})
    if not ruc.isdigit() or len(ruc) != 11:
        raise ValidationError({'ruc': 'El RUC debe tener 11 dígitos.'})
    if Empresa.objects.filter(ruc=ruc).exists():
        raise ValidationError({'ruc': 'Ya existe una empresa con ese RUC.'})
    if not admin_email or '@' not in admin_email:
        raise ValidationError({'admin_email': 'Email del administrador inválido.'})
    if User.objects.filter(email__iexact=admin_email).exists():
        raise ValidationError({'admin_email': 'Ya existe un usuario con ese email.'})
    if not admin_password or len(admin_password) < 8:
        raise ValidationError({'admin_password': 'La contraseña debe tener al menos 8 caracteres.'})

    empresa = Empresa.objects.create(nombre=nombre, ruc=ruc, modo_inventario=modo_inventario,
                                     **datos_empresa)
    usuario = User(
        email=admin_email, username=admin_email,
        nombre=admin_nombre or '', apellido=admin_apellido or '',
        empresa=empresa, rol='admin', is_active=True, is_staff=False, is_superuser=False,
    )
    usuario.set_password(admin_password)
    usuario.save()
    return empresa, usuario
