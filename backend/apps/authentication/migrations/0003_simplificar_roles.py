from django.db import migrations, models

# Simplificación de roles: 7 → 3 (admin, operador, solo_lectura).
# Mapeo hacia adelante: readonly → solo_lectura; comercial/produccion/
# almacen/contador/personalizado → operador; admin queda igual.
# El reverso es con pérdida (operador no distingue el matiz original):
# solo_lectura → readonly y operador → comercial, documentado en ENTREGA.md.

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
