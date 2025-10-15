from django.contrib import admin
from django.db import transaction
from django.contrib import messages
from .models import Venta, DetalleVenta, Cliente, Factura, OrdenVenta, ComprobantePago, PagoVenta
from apps.empresas.models import Empresa
from apps.inventario.models import Producto
from django import forms
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.db.models.functions import Coalesce


class DetalleVentaInlineFormSet(forms.models.BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        if any(self.errors):
            return
            
        # Validar que haya al menos un detalle
        detalles_validos = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                detalles_validos += 1
                
                # Validar que cantidad y precio sean positivos
                cantidad = form.cleaned_data.get('cantidad', 0)
                precio = form.cleaned_data.get('precio_unitario', 0)
                if cantidad <= 0:
                    raise forms.ValidationError('La cantidad debe ser mayor que cero.')
                if precio <= 0:
                    raise forms.ValidationError('El precio debe ser mayor que cero.')
                    
        if detalles_validos == 0:
            raise forms.ValidationError('Debe agregar al menos un detalle.')

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    formset = DetalleVentaInlineFormSet
    extra = 1
    min_num = 1
    validate_min = True
    can_delete = True
    fields = ['producto', 'cantidad', 'precio_unitario']
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.request = request
        return formset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "producto":
            if not request.user.is_superuser:
                kwargs["queryset"] = Producto.objects.filter(empresa=request.user.empresa)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'cliente', 'fecha_emision', 'fecha_vencimiento',
        'tipo_venta', 'estado', 'total', 'get_saldo_pendiente'
    ]
    list_filter = [
        'estado', 'tipo_venta', 'metodo_pago',
        'igv_incluido', 'fecha_emision', 'fecha_vencimiento'
    ]
    search_fields = [
        'numero', 'cliente__nombre',
        'cliente__documento', 'notas', 'referencia'
    ]
    date_hierarchy = 'fecha_emision'
    inlines = [DetalleVentaInline]
    readonly_fields = (
        'numero', 'subtotal', 'igv', 'total',
        'get_saldo_pendiente', 'fecha_creacion',
        'fecha_modificacion'
    )
    
    fieldsets = (
        ('Información General', {
            'fields': (
                'empresa', 'cliente', 'fecha_emision',
                'fecha_vencimiento', 'tipo_venta'
            )
        }),
        ('Estado y Método de Pago', {
            'fields': (
                'estado', 'metodo_pago', 'igv_incluido'
            )
        }),
        ('Información de Pagos', {
            'fields': (
                'total', 'get_saldo_pendiente'
            )
        }),
        ('Información Adicional', {
            'fields': (
                'notas', 'referencia', 'comprobante'
            ),
            'classes': ('collapse',)
        }),
        ('Información del Sistema', {
            'fields': (
                'fecha_creacion', 'fecha_modificacion'
            ),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si estamos editando un objeto existente
            return self.readonly_fields + ('tipo_venta', 'empresa')
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Si es una nueva venta
            if not request.user.is_superuser:
                if not hasattr(request.user, 'empresa') or not request.user.empresa:
                    raise PermissionDenied("El usuario no tiene una empresa asignada")
                
                # Configurar empresa por defecto y hacerla read-only
                form.base_fields['empresa'].initial = request.user.empresa
                form.base_fields['empresa'].disabled = True
                
                # Filtrar clientes por empresa
                form.base_fields['cliente'].queryset = Cliente.objects.filter(
                    empresa=request.user.empresa,
                    activo=True
                ).order_by('nombre')
        return form

    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva venta
            if not hasattr(request.user, 'empresa') or not request.user.empresa:
                raise PermissionDenied("El usuario no tiene una empresa asignada")
            obj.empresa = request.user.empresa
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'empresa') and request.user.empresa:
                qs = qs.filter(empresa=request.user.empresa)
            else:
                qs = qs.none()  # No mostrar nada si no tiene empresa
        return qs

    def get_saldo_pendiente(self, obj):
        return obj.get_saldo_pendiente()
    get_saldo_pendiente.short_description = 'Saldo Pendiente'

    def get_estado_vencimiento(self, obj):
        if not obj.fecha_vencimiento:
            return 'Sin vencimiento'
        if obj.estado == 'pagada':
            return 'Pagada'
        hoy = timezone.now().date()
        if obj.fecha_vencimiento < hoy:
            return 'Vencida'
        return 'Pendiente'
    get_estado_vencimiento.short_description = 'Estado Vencimiento'

    def marcar_como_pagada(self, request, queryset):
        for venta in queryset:
            try:
                venta.marcar_como_pagada()
                self.message_user(request, f'Venta {venta.numero} marcada como pagada exitosamente.')
            except Exception as e:
                self.message_user(request, f'Error al marcar venta {venta.numero} como pagada: {str(e)}', level=messages.ERROR)
    marcar_como_pagada.short_description = "Marcar ventas seleccionadas como pagadas"

    def anular_ventas(self, request, queryset):
        for venta in queryset:
            try:
                venta.anular_venta()
                self.message_user(request, f'Venta {venta.numero} anulada exitosamente.')
            except Exception as e:
                self.message_user(request, f'Error al anular venta {venta.numero}: {str(e)}', level=messages.ERROR)
    anular_ventas.short_description = "Anular ventas seleccionadas"

    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        try:
            with transaction.atomic():
                venta = form.instance
                if not venta.pk:
                    venta.save()
                
                instances = formset.save(commit=False)
                
                for obj in formset.deleted_objects:
                    obj.delete()
                
                for instance in instances:
                    if not instance.venta_id:
                        instance.venta = venta
                    instance.save()
                
                formset.save_m2m()
                venta.actualizar_totales()
                
                if venta.estado == 'pagada':
                    venta.actualizar_stock()
                
        except Exception as e:
            self.message_user(request, f"Error al guardar los detalles: {str(e)}", level=messages.ERROR)
            raise

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'documento', 'tipo_documento', 'email', 'telefono', 'activo']
    list_filter = ['activo', 'tipo_documento']
    search_fields = ['nombre', 'documento', 'email']
    exclude = ['usuario']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(empresa=request.user.empresa)
        return qs

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero_factura', 'cliente', 'fecha', 'total']
    list_filter = ['fecha']
    search_fields = ['numero_factura', 'cliente__nombre']

@admin.register(OrdenVenta)
class OrdenVentaAdmin(admin.ModelAdmin):
    list_display = ['numero_orden', 'cliente', 'fecha_orden', 'estado', 'total']
    list_filter = ['estado', 'fecha_orden']
    search_fields = ['numero_orden', 'cliente__nombre']

@admin.register(PagoVenta)
class PagoVentaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'venta', 'fecha', 'monto',
        'metodo_pago', 'get_tipo_venta',
        'get_saldo_pendiente'
    ]
    list_filter = [
        'metodo_pago',
        'fecha',
        'venta__tipo_venta'
    ]
    search_fields = [
        'venta__numero',
        'venta__cliente__nombre',
        'referencia'
    ]
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'venta', 'fecha', 'monto',
                'metodo_pago'
            )
        }),
        ('Información Adicional', {
            'fields': (
                'referencia', 'comprobante',
                'notas'
            ),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si estamos editando un pago existente
            return ['venta']
        return []

    def get_tipo_venta(self, obj):
        return obj.venta.get_tipo_venta_display()
    get_tipo_venta.short_description = 'Tipo de Venta'

    def get_saldo_pendiente(self, obj):
        return obj.venta.get_saldo_pendiente()
    get_saldo_pendiente.short_description = 'Saldo Pendiente'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "venta":
            # Filtrar solo ventas pendientes o con saldo pendiente
            kwargs["queryset"] = Venta.objects.filter(
                estado='pendiente'
            ).exclude(
                estado='anulado'
            ).annotate(
                saldo_pendiente=models.F('total') - Coalesce(
                    models.Sum('pagos__monto'),
                    0
                )
            ).filter(
                saldo_pendiente__gt=0
            )
            
            if not request.user.is_superuser:
                kwargs["queryset"] = kwargs["queryset"].filter(
                    empresa=request.user.empresa
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        try:
            with transaction.atomic():
                super().save_model(request, obj, form, change)
                # Actualizar el estado de la venta
                obj.venta.actualizar_estado_pago()
        except ValidationError as e:
            self.message_user(request, str(e), level=messages.ERROR)
            raise

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = ['venta', 'fecha_subida', 'tipo']
    list_filter = ['tipo', 'fecha_subida']
    search_fields = ['venta__numero', 'numero']
    date_hierarchy = 'fecha_subida'