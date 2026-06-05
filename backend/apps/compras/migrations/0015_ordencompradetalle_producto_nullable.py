from django.db import migrations


class Migration(migrations.Migration):
    """
    Hace producto_id nullable en compras_ordencompradetalle.
    La tabla tiene managed=False → SeparateDatabaseAndState.
    La migración 0001 creó producto_id como NOT NULL FK.
    """

    dependencies = [
        ('compras', '0014_oc_moneda_formapago_descripcion'),
        ('inventario', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE compras_ordencompradetalle ALTER COLUMN producto_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE compras_ordencompradetalle ALTER COLUMN producto_id SET NOT NULL;",
                ),
            ],
            state_operations=[],
        ),
    ]
