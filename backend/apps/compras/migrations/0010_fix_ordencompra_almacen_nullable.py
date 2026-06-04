from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    almacen_id exists in compras_ordencompra as NOT NULL (from 0001_initial)
    but was removed from the model without a migration.  Django therefore omits
    it from INSERT statements, which violates the NOT NULL constraint → 500.

    SeparateDatabaseAndState lets us:
      - Tell Django's state that the field is now nullable (AlterField in state_operations)
      - Drop the NOT NULL constraint on the existing column (RunSQL in database_operations)
        without touching the FK itself (column + index already exist).
    """

    dependencies = [
        ('compras', '0009_fix_ordencompra_fecha_emision'),
        ('inventario', '0010_add_marca_producto'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE compras_ordencompra ALTER COLUMN almacen_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE compras_ordencompra ALTER COLUMN almacen_id SET NOT NULL;",
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='ordencompra',
                    name='almacen',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ordenes_compra',
                        to='inventario.almacen',
                    ),
                ),
            ],
        ),
    ]
