from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'nombre', 'apellido', 'empresa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['nombre'].required = True
        self.fields['apellido'].required = True

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('email', 'nombre', 'apellido', 'empresa')

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('email', 'nombre', 'apellido', 'empresa', 'rol', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'empresa', 'rol')
    search_fields = ('email', 'nombre', 'apellido')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('nombre', 'apellido', 'empresa')}),
        ('Rol y Permisos', {'fields': ('rol', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellido', 'password1', 'password2', 'empresa', 'rol'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es una creación nueva
            obj.username = obj.email.split('@')[0]  # Usar la parte local del email como username inicial
        super().save_model(request, obj, form, change)

admin.site.register(CustomUser, CustomUserAdmin) 