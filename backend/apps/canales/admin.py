"""Admin del canal (C2): MensajeConversacion guarda texto libre de los
usuarios, así que el admin lo acota por empresa con el MISMO patrón que
ventas/compras (staff ve solo su empresa; superusuario ve todo). Solo lectura:
la memoria del chat no se edita a mano."""
from django.contrib import admin

from .models import BorradorAgente, MensajeConversacion


class EmpresaScopedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'empresa') and request.user.empresa:
                qs = qs.filter(empresa=request.user.empresa)
            else:
                qs = qs.none()
        return qs


@admin.register(MensajeConversacion)
class MensajeConversacionAdmin(EmpresaScopedAdmin):
    list_display = ('created_at', 'empresa', 'usuario', 'id_externo', 'rol', 'texto_corto')
    list_filter = ('rol', 'canal')
    search_fields = ('id_externo',)
    date_hierarchy = 'created_at'

    def texto_corto(self, obj):
        return obj.texto[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BorradorAgente)
class BorradorAgenteAdmin(EmpresaScopedAdmin):
    list_display = ('created_at', 'empresa', 'usuario', 'tipo', 'estado', 'documento_numero')
    list_filter = ('tipo', 'estado')
