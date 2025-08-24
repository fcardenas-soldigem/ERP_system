from django.contrib import admin
from django.forms import ModelForm
from .models import Compra, Proveedor, CompraDetalle, PagoCompra, ComprobantePago
from apps.inventario.models import Almacen, Producto
from apps.empresas.models import Empresa
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.html import format_html
from datetime import timedelta
from django import forms

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'ruc', 'telefono', 'empresa', 'activo')
    search_fields = ('razon_social', 'ruc')
    list_filter = ('activo', 'empresa')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(empresa=request.user.empresa)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == "empresa":
            kwargs["queryset"] = Empresa.objects.filter(id=request.user.empresa.id)
            kwargs["initial"] = request.user.empresa
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo proveedor
            if not obj.empresa_id and hasattr(request.user, 'empresa'):
                obj.empresa = request.user.empresa
        super().save_model(request, obj, form, change)

class CompraDetalleInlineFormSet(forms.models.BaseInlineFormSet):
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

class CompraDetalleInline(admin.TabularInline):
    model = CompraDetalle
    extra = 1
    fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal', 'igv', 'total']
    readonly_fields = ['subtotal', 'igv', 'total']
    autocomplete_fields = ['producto']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(compra__empresa=request.user.empresa)
        return qs

class CompraForm(ModelForm):
    class Meta:
        model = Compra
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        tipo_compra = cleaned_data.get('tipo_compra')
        fecha_vencimiento = cleaned_data.get('fecha_vencimiento')

        if tipo_compra in ['credito_30', 'credito_60'] and not fecha_vencimiento:
            self.add_error('fecha_vencimiento', 'Este campo es requerido para compras a crédito')
        
        return cleaned_data

@admin.register(CompraDetalle)
class CompraDetalleAdmin(admin.ModelAdmin):
    list_display = [
        'compra',
        'producto',
        'cantidad',
        'precio_unitario',
        'subtotal',
        'igv',
        'total'
    ]
    list_filter = [
        'compra__estado',
        'compra__fecha_emision',
        'created_at'
    ]
    search_fields = [
        'compra__numero',
        'producto__nombre',
        'producto__sku'
    ]
    readonly_fields = [
        'subtotal',
        'igv',
        'total',
        'created_at',
        'updated_at'
    ]
    autocomplete_fields = ['compra', 'producto']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(compra__empresa=request.user.empresa)
        return qs

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    form = CompraForm
    inlines = [CompraDetalleInline]
    list_display = [
        'numero', 
        'empresa', 
        'proveedor', 
        'fecha_emision', 
        'fecha_vencimiento',
        'tipo_compra',
        'estado',
        'total',
        'get_saldo_pendiente'
    ]
    list_filter = [
        'estado', 
        'tipo_compra', 
        'metodo_pago',
        'igv_incluido', 
        'fecha_emision', 
        'fecha_vencimiento'
    ]
    search_fields = [
        'numero', 
        'proveedor__razon_social',
        'proveedor__ruc'
    ]
    readonly_fields = [
        'numero',
        'subtotal', 
        'igv', 
        'total',
        'get_saldo_pendiente',
        'created_at',
        'updated_at'
    ]
    autocomplete_fields = ['proveedor', 'almacen']
    
    fieldsets = (
        ('Información General', {
            'fields': (
                'empresa',
                'proveedor',
                'almacen',
                'fecha_emision',
                'fecha_vencimiento',
                'numero'
            )
        }),
        ('Estado y Configuración', {
            'fields': (
                'estado',
                'tipo_compra',
                'metodo_pago',
                'igv_incluido'
            )
        }),
        ('Información de Pagos', {
            'fields': (
                'subtotal',
                'igv',
                'total',
                'get_saldo_pendiente'
            )
        }),
        ('Información Adicional', {
            'fields': (
                'notas',
                'referencia',
                'comprobante'
            ),
            'classes': ('collapse',)
        }),
        ('Información del Sistema', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si estamos editando un objeto existente
            return self.readonly_fields + ('tipo_compra',)
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:  # Si es una nueva compra
            if not request.user.is_superuser:
                if not hasattr(request.user, 'empresa'):
                    raise PermissionError("El usuario no tiene una empresa asignada")
                
                form.base_fields['empresa'].initial = request.user.empresa
                form.base_fields['empresa'].disabled = True
                
                form.base_fields['proveedor'].queryset = Proveedor.objects.filter(
                    empresa=request.user.empresa,
                    activo=True
                ).order_by('razon_social')
                
                form.base_fields['almacen'].queryset = Almacen.objects.filter(
                    empresa=request.user.empresa,
                    is_active=True
                ).order_by('nombre')
        return form

    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva compra
            if not obj.empresa_id and hasattr(request.user, 'empresa'):
                obj.empresa = request.user.empresa
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(empresa=request.user.empresa)
        return qs

    def get_saldo_pendiente(self, obj):
        saldo = obj.get_saldo_pendiente()
        if saldo > 0:
            return format_html('<span style="color: red;">{}</span>', saldo)
        return format_html('<span style="color: green;">0.00</span>')
    get_saldo_pendiente.short_description = 'Saldo Pendiente'

    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        try:
            with transaction.atomic():
                compra = form.instance
                if not compra.pk:
                    compra.save()
                
                instances = formset.save(commit=False)
                
                for obj in formset.deleted_objects:
                    obj.delete()
                
                for instance in instances:
                    if not instance.compra_id:
                        instance.compra = compra
                    instance.save()
                
                formset.save_m2m()
                compra.actualizar_totales()
                
                if compra.estado == 'pagada':
                    compra.actualizar_stock()
                
        except Exception as e:
            self.message_user(request, f"Error al guardar los detalles: {str(e)}", level=messages.ERROR)
            raise

    def tipo_compra_display(self, obj):
        colors = {
            'contado': '#34a853',
            'credito_30': '#1a73e8',
            'credito_60': '#1a73e8'
        }
        labels = {
            'contado': 'Contado',
            'credito_30': 'Crédito 30 días',
            'credito_60': 'Crédito 60 días'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.tipo_compra, 'black'),
            labels.get(obj.tipo_compra, obj.tipo_compra)
        )
    tipo_compra_display.short_description = 'Tipo de Compra'

    def estado_display(self, obj):
        colors = {
            'borrador': '#f29339',
            'pendiente': '#1a73e8',
            'pagada': '#34a853',
            'anulada': '#ea4335'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.estado, 'black'),
            obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'

@admin.register(PagoCompra)
class PagoCompraAdmin(admin.ModelAdmin):
    list_display = [
        'compra',
        'fecha',
        'monto',
        'metodo_pago',
        'referencia'
    ]
    list_filter = ['compra__empresa', 'fecha', 'metodo_pago']
    search_fields = ['compra__numero', 'referencia']
    raw_id_fields = ['compra']

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "metodo_pago":
            kwargs['choices'] = [
                ('efectivo', 'Efectivo'),
                ('transferencia', 'Transferencia'),
                ('cheque', 'Cheque'),
                ('tarjeta', 'Tarjeta')
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo pago
            saldo_pendiente = obj.compra.get_saldo_pendiente()
            if obj.monto > saldo_pendiente:
                raise ValidationError(f"El monto del pago (${obj.monto}) no puede ser mayor al saldo pendiente (${saldo_pendiente})")
        
        super().save_model(request, obj, form, change)
        obj.compra.actualizar_estado_pago()

@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = ['compra', 'tipo', 'numero', 'fecha_subida']
    list_filter = ['tipo', 'fecha_subida']
    search_fields = ['compra__numero', 'numero']
    raw_id_fields = ['compra']