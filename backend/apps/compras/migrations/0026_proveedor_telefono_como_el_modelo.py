from django.db import migrations

# Bug real de prod (lo destapó la reparación de la cadena, ver 0002_squashed):
# compras_proveedor.telefono quedó varchar(9) NOT NULL en la BD porque el
# AlterField de 0007 nunca se ejecutó allí. El modelo dice
# CharField(max_length=15, null=True, blank=True): crear un proveedor sin
# teléfono → IntegrityError (500); con «+51 999 888 777» → DataError.
#
# Solo BD (el estado de Django ya es el correcto). En prod: ensancha y relaja,
# sin reescribir ni perder filas.


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0025_alter_compra_comprobante_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE compras_proveedor ALTER COLUMN telefono TYPE varchar(15); "
                "ALTER TABLE compras_proveedor ALTER COLUMN telefono DROP NOT NULL;"
            ),
            # no se vuelve a NOT NULL/varchar(9): fallaría con datos válidos nuevos
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
