from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
import logging

logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )

    # Tres roles, sin matices: la defensa real vive en el backend
    # (core.permissions.RolEscritura). solo_lectura no puede escribir nada.
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('operador', 'Operador'),
        ('solo_lectura', 'Solo lectura'),
    ]
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='operador',
        help_text='admin: todo; operador: trabaja con documentos; solo_lectura: solo consulta.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        if not self.username:
            # Generar un username único basado en el email
            base_username = self.email.split('@')[0]
            username = base_username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)

@receiver(post_save, sender=CustomUser)
def create_user_empresa(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo usuario, si no tiene empresa asignada,
    se crea una nueva empresa para él.
    """
    from apps.empresas.models import Empresa  # Importación local para evitar importación circular
    
    if created and not instance.empresa and not instance.is_superuser:
        # Crear una nueva empresa para el usuario
        empresa = Empresa.objects.create(
            nombre=f"Empresa de {instance.nombre} {instance.apellido}",
            ruc=get_random_string(11, '0123456789'),  # Genera un RUC temporal
            direccion="Pendiente de actualizar",
            telefono="",  # Empresa.telefono es varchar(9); el placeholder anterior (23 chars) reventaba en Postgres
            email=instance.email
        )
        
        # Asignar la empresa al usuario
        instance.empresa = empresa
        instance.save() 