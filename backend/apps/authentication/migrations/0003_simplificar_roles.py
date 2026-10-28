from django.db import migrations, models

# Simplificación de roles: 7 → 3 (admin, operador, solo_lectura).
#
# Mapeo hacia adelante:
#   readonly → solo_lectura; comercial/produccion/almacen/contador/personalizado
#   → operador; admin queda igual.
# Salvaguardas (nunca degradar a quien administra):
#   1. superusuarios y is_staff → admin (antes ModulePermission ya los trataba
#      como admin; con el rol por defecto 'readonly' habrían quedado sin poder
#      escribir).
#   2. Ninguna empresa queda sin admin: si tras el mapeo una empresa no tiene
#      ningún admin, su usuario más antiguo (activo si lo hay) pasa a admin.
#
# El reverso es con pérdida (operador no distingue el matiz original):
# solo_lectura → readonly y operador → comercial; los ascendidos a admin por
# las salvaguardas se quedan admin. Documentado en ENTREGA.md.

HACIA_ADELANTE = {
    'readonly': 'solo_lectura',
    'comercial': 'operador',
    'produccion': 'operador',
    'almacen': 'operador',
    'contador': 'operador',
    'personalizado': 'operador',
}
HACIA_ATRAS = {
    'solo_lectura': 'readonly',
    'operador': 'comercial',
}


def adelante(apps, schema_editor):
    User = apps.get_model('authentication', 'CustomUser')

    for viejo, nuevo in HACIA_ADELANTE.items():
        User.objects.filter(rol=viejo).update(rol=nuevo)

    # 1. quien administra la plataforma nunca queda degradado
    User.objects.filter(is_superuser=True).exclude(rol='admin').update(rol='admin')
    User.objects.filter(is_staff=True).exclude(rol='admin').update(rol='admin')

    # 2. ninguna empresa sin admin
    empresas_con_usuarios = (User.objects.exclude(empresa_id=None)
                             .values_list('empresa_id', flat=True).distinct())
    for empresa_id in empresas_con_usuarios:
        usuarios = User.objects.filter(empresa_id=empresa_id)
        if usuarios.filter(rol='admin', is_active=True).exists():
            continue
        mas_antiguo = (usuarios.filter(is_active=True).order_by('date_joined', 'id').first()
                       or usuarios.order_by('date_joined', 'id').first())
        User.objects.filter(pk=mas_antiguo.pk).update(rol='admin')


def atras(apps, schema_editor):
    User = apps.get_model('authentication', 'CustomUser')
    for nuevo, viejo in HACIA_ATRAS.items():
        User.objects.filter(rol=nuevo).update(rol=viejo)


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_customuser_rol'),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
        migrations.AlterField(
            model_name='customuser',
            name='rol',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrador'),
                    ('operador', 'Operador'),
                    ('solo_lectura', 'Solo lectura'),
                ],
                default='operador',
                help_text='admin: todo; operador: trabaja con documentos; solo_lectura: solo consulta.',
                max_length=20,
            ),
        ),
    ]
