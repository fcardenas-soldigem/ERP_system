from django.db import migrations, models


class Migration(migrations.Migration):
    """
    fecha_actualizacion fue eliminada del estado Django por 0007_add_moneda_to_pagocompra
    (RemoveField en state), pero la columna sigue existiendo en la BD porque fue
    re-agregada manualmente. Esta migración sincroniza el estado Django sin tocar la BD.
    """

    dependencies = [
        ('compras', '0011_fix_ordencompra_proveedor_complete'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='ordencompra',
                    name='fecha_actualizacion',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
        ),
    ]
