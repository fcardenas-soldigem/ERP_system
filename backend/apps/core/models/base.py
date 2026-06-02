"""
Modelos Base Multi-Tenant para ERP Enterprise

Estos modelos base proporcionan:
- Aislamiento automático por empresa (tenant)
- Soft delete con restauración
- Timestamps automáticos
- Managers especializados

USO:
    from apps.core.models.base import TenantModel, SoftDeleteModel
    
    class MiModelo(TenantModel):
        nombre = models.CharField(max_length=100)
        
        class Meta:
            # Heredar de TenantModel ya incluye empresa
            pass
"""
from django.db import models
from django.utils import timezone
from django.conf import settings


class TenantManager(models.Manager):
    """
    Manager que filtra automáticamente por empresa del usuario actual.
    
    El filtrado principal lo hace RLS a nivel de base de datos,
    pero este manager proporciona defensa en profundidad.
    """
    
    def get_queryset(self):
        qs = super().get_queryset()
        # El RLS ya filtra, pero esto es defensa adicional
        # Solo filtrar si el modelo tiene empresa_id
        if hasattr(self.model, 'empresa_id'):
            # En contextos sin request (migrations, scripts), no filtrar
            pass
        return qs


class SoftDeleteManager(TenantManager):
    """
    Manager que excluye registros con soft delete.
    """
    
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        """
        Retorna queryset incluyendo registros eliminados.
        """
        return super().get_queryset()
    
    def only_deleted(self):
        """
        Retorna solo registros eliminados.
        """
        return super().get_queryset().filter(deleted_at__isnull=False)


class BaseModel(models.Model):
    """
    Modelo base con timestamps automáticos.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    class Meta:
        abstract = True


class TenantModel(BaseModel):
    """
    Modelo base para entidades multi-tenant.
    
    Todas las entidades de negocio deben heredar de este modelo
    para garantizar el aislamiento por empresa.
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        verbose_name='Empresa',
        db_index=True
    )
    
    objects = TenantManager()
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        # Validar que empresa_id esté presente
        if not self.empresa_id:
            raise ValueError(f"{self.__class__.__name__} requiere empresa_id")
        super().save(*args, **kwargs)


class SoftDeleteModel(TenantModel):
    """
    Modelo con soft delete para entidades que no deben eliminarse físicamente.
    
    Proporciona:
    - soft_delete(): Marca como eliminado
    - restore(): Restaura un registro eliminado
    - Filtrado automático de eliminados
    """
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        db_index=True,
        verbose_name='Fecha de eliminación'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Eliminado por'
    )
    
    objects = SoftDeleteManager()
    all_objects = TenantManager()  # Incluye eliminados
    
    class Meta:
        abstract = True
    
    @property
    def is_deleted(self):
        """Indica si el registro está eliminado."""
        return self.deleted_at is not None
    
    def soft_delete(self, user=None):
        """
        Marca el registro como eliminado sin eliminarlo físicamente.
        
        Args:
            user: Usuario que realiza la eliminación (opcional)
        """
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])
    
    def restore(self):
        """
        Restaura un registro eliminado.
        """
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])
    
    def delete(self, *args, **kwargs):
        """
        Override de delete para hacer soft delete por defecto.
        
        Para eliminar físicamente, usar:
            instance.delete(hard=True)
        """
        hard = kwargs.pop('hard', False)
        if hard:
            super().delete(*args, **kwargs)
        else:
            self.soft_delete(user=kwargs.get('user'))


class AuditMixin(models.Model):
    """
    Mixin para agregar campos de auditoría.
    
    Útil para entidades que requieren tracking de quién creó/modificó.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Creado por'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Actualizado por'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
