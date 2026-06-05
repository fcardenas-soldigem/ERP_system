from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Añade moneda y forma_pago a OrdenCompra (managed).
    Añade descripcion a OrdenCompraDetalle (managed=False → SeparateDatabaseAndState).
    """

    dependencies = [
        ('compras', '0013_restore_ordencompradetalle_managed_false'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordencompra',
            name='moneda',
            field=models.CharField(
                choices=[('PEN', 'Sol Peruano (S/)'), ('USD', 'Dólar Americano ($)')],
                default='USD',
                max_length=3,
                verbose_name='Moneda',
            ),
        ),
        migrations.AddField(
            model_name='ordencompra',
            name='forma_pago',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='Forma de Pago',
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE compras_ordencompradetalle ADD COLUMN IF NOT EXISTS descripcion VARCHAR(500) NULL;",
                    reverse_sql="ALTER TABLE compras_ordencompradetalle DROP COLUMN IF EXISTS descripcion;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='ordencompradetalle',
                    name='descripcion',
                    field=models.CharField(blank=True, max_length=500, null=True),
                ),
            ],
        ),
    ]
