from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Dos campos de compras_ordencompra están desincronizados entre BD y modelo:

    1. proveedor_id: EXISTS en BD como NOT NULL FK (0001_initial AddField) pero
       fue eliminado de models.py sin migración. Django lo omite en INSERT
       → NOT NULL violation → 500 en POST /api/compras/ordenes/.
       Fix: DROP NOT NULL en BD + AlterField en estado (null=True).

    2. proveedor_nombre: EXISTS en BD como NOT NULL con default '' (agregado
       directamente a la BD) pero nunca fue migrado. Django's migration state
       no lo conoce, y el modelo lo define como null=True (mismatch).
       Fix: DROP NOT NULL en BD + AddField en estado para sincronizar.
    """

    dependencies = [
        ('compras', '0010_fix_ordencompra_almacen_nullable'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # 1. proveedor_id: quitar NOT NULL para que INSERTs sin proveedor no fallen
                migrations.RunSQL(
                    sql="ALTER TABLE compras_ordencompra ALTER COLUMN proveedor_id DROP NOT NULL;",
                    reverse_sql="ALTER TABLE compras_ordencompra ALTER COLUMN proveedor_id SET NOT NULL;",
                ),
                # 2. proveedor_nombre: ya existe en BD como NOT NULL, hacerlo nullable
                #    para que coincida con el modelo (CharField null=True)
                migrations.RunSQL(
                    sql="ALTER TABLE compras_ordencompra ALTER COLUMN proveedor_nombre DROP NOT NULL;",
                    reverse_sql="ALTER TABLE compras_ordencompra ALTER COLUMN proveedor_nombre SET NOT NULL;",
                ),
            ],
            state_operations=[
                # Sincronizar proveedor FK → null=True (columna ya existe, sólo cambio de estado)
                migrations.AlterField(
                    model_name='ordencompra',
                    name='proveedor',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ordenes_compra',
                        to='compras.proveedor',
                    ),
                ),
                # Registrar proveedor_nombre en estado Django (columna ya existe en BD)
                migrations.AddField(
                    model_name='ordencompra',
                    name='proveedor_nombre',
                    field=models.CharField(blank=True, max_length=200, null=True),
                ),
            ],
        ),
    ]
