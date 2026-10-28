"""
Squash de reparación de compras 0002–0009 (NO edita migraciones aplicadas).

Por qué existe: 0001_initial se regeneró introspectando la BD real, y la
historia 0002–0009 choca con él en una BD LIMPIA (tests, staging nuevo):
  - 0002 y 0003 vuelven a añadir columnas que 0001 ya crea
    («column created_at/comprobante already exists»);
  - 0007 elimina de ordencompra almacen/fecha_emision/proveedor/
    fecha_actualizacion y el modelo OrdenCompraDetalle, cosa que en la BD real
    NUNCA se ejecutó (0009–0013 asumen esas columnas y esa tabla presentes);
  - 0009 hace ALTER sobre una columna que en una BD limpia 0007 ya borró.

Cómo funciona (`replaces`, mecanismo estándar de Django):
  - En PROD las 8 migraciones reemplazadas ya están aplicadas → Django da esta
    por aplicada y NO ejecuta nada. Las originales quedan intactas.
  - En una BD LIMPIA se usa esta en lugar de las 8: mismas operaciones, pero
    las que en prod nunca tocaron la BD van como solo-estado y 0009 usa
    ADD COLUMN IF NOT EXISTS.
Además reproduce en la BD limpia la deriva REAL de prod en estas tablas (todo
lo que prod tiene marcado como aplicado pero nunca ejecutó queda como «solo
estado», y los DEFAULT puestos a mano se replican): así tests y entornos nuevos
se comportan como prod. Esa deriva incluye dos bugs de prod que NO se corrigen
aquí (requieren migración nueva con revisión de datos, ver DEPLOY.md §11):
compras_compra sin unique (empresa, numero) y compras_comprarecurrente con
columnas NOT NULL que el modelo ya no tiene.
Verificado: esquema final de BD limpia == esquema de prod en compras_* (diff
de columnas, defaults, restricciones e índices).
"""
import datetime

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ('compras', '0002_add_timestamps_to_pagocompra'),
        ('compras', '0003_add_comprobante_to_compra'),
        ('compras', '0004_alter_compradetalle_options_compradetalle_created_at_and_more'),
        ('compras', '0005_fix_comprarecurrente_temp'),
        ('compras', '0006_add_moneda_to_compra'),
        ('compras', '0007_add_moneda_to_pagocompra'),
        ('compras', '0008_change_numero_unique_per_empresa'),
        ('compras', '0009_fix_ordencompra_fecha_emision'),
    ]

    dependencies = [
        ('compras', '0001_initial'),
        ('inventario', '0004_alter_producto_sku_alter_categoria_unique_together_and_more'),
        ('empresas', '0002_empresa_logo'),
    ]

    operations = [
        # ── 0002_add_timestamps_to_pagocompra ──

        # ── 0003_add_comprobante_to_compra ──
        # La columna ya existe en BD (0001_initial regenerado la incluye); solo estado.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='compra',
                    name='comprobante',
                    field=models.FileField(blank=True, null=True, upload_to='comprobantes/compras/'),
                ),
            ],
        ),
        # ── 0004_alter_compradetalle_options_compradetalle_created_at_and_more ──
        migrations.AlterModelOptions(
            name='compradetalle',
            options={'ordering': ['id'], 'verbose_name': 'Detalle de Compra', 'verbose_name_plural': 'Detalles de Compra'},
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='igv',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='notas',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='compradetalle',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='compradetalle',
            name='producto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='detalles_compra', to='inventario.producto'),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='comprobantes/pagos/'),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='fecha',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='metodo_pago',
            field=models.CharField(choices=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'), ('cheque', 'Cheque'), ('tarjeta', 'Tarjeta'), ('pendiente', 'Pendiente')], default='efectivo', max_length=20),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='referencia',
            field=models.CharField(blank=True, help_text='Número de operación, cheque, etc.', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='pagocompra',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        # ── 0005_fix_comprarecurrente_temp ──
        # Migración vacía - los cambios ya se aplicaron manualmente
        # ── 0006_add_moneda_to_compra ──
        migrations.AddField(
            model_name='compra',
            name='moneda',
            field=models.CharField(
                choices=[('PEN', 'Sol Peruano (S/)'), ('USD', 'Dólar Americano ($)')],
                default='PEN',
                max_length=3,
                verbose_name='Moneda'
            ),
        ),
        # ── 0007_add_moneda_to_pagocompra ──
        migrations.AlterModelOptions(
            name='ordencompra',
            options={'ordering': ['-fecha_creacion'], 'verbose_name': 'Orden de Compra', 'verbose_name_plural': 'Órdenes de Compra'},
        ),
        # En prod esto nunca llegó a la BD (aplicada en falso): solo estado.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='comprarecurrente',
                    unique_together=set(),
                ),
            ],
        ),
        # en prod la columna quedó NOT NULL DEFAULT '' (no como dice el modelo)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE compras_comprarecurrente "
                        "ADD COLUMN proveedor_nombre varchar(200) NOT NULL DEFAULT '';",
                    reverse_sql="ALTER TABLE compras_comprarecurrente DROP COLUMN proveedor_nombre;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='comprarecurrente',
                    name='proveedor_nombre',
                    field=models.CharField(blank=True, max_length=200, null=True),
                ),
            ],
        ),
        migrations.AddField(
            model_name='ordencompra',
            name='proveedor_nombre',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='pagocompra',
            name='moneda',
            field=models.CharField(choices=[('PEN', 'Sol Peruano (S/)'), ('USD', 'Dólar Americano ($)')], default='PEN', max_length=3, verbose_name='Moneda del pago'),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='direccion',
            field=models.TextField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='email',
            field=models.EmailField(blank=True, max_length=100, null=True),
        ),
        # En prod esto nunca llegó a la BD (aplicada en falso): solo estado.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='proveedor',
                    name='telefono',
                    field=models.CharField(blank=True, max_length=15, null=True),
                ),
            ],
        ),
        # En prod esto nunca llegó a la BD (aplicada en falso): solo estado.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='comprarecurrente',
                    unique_together={('empresa', 'proveedor_nombre', 'concepto')},
                ),
            ],
        ),
        # La tabla compras_ordencompradetalle la posee el purchase-orders-service
        # (0013 la re-declara managed=False). En la BD real nunca se eliminó;
        # se borra solo del estado para que la BD limpia la conserve.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='OrdenCompraDetalle'),
            ],
        ),
        # En prod esto nunca llegó a la BD (aplicada en falso): solo estado. Prod conserva las 9 columnas.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='almacen',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='created_at',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='descripcion',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='dia_pago',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='fecha_ultima_compra',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='igv_incluido',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='proveedor',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='ultima_compra',
                ),
                migrations.RemoveField(
                    model_name='comprarecurrente',
                    name='updated_at',
                ),
            ],
        ),
        # En la BD legada estas columnas de ordencompra nunca se eliminaron
        # (la migración se aplicó en falso) y las migraciones 0009-0012 las
        # asumen presentes. Solo se quitan del estado; la BD las conserva.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='ordencompra',
                    name='almacen',
                ),
                migrations.RemoveField(
                    model_name='ordencompra',
                    name='fecha_actualizacion',
                ),
                migrations.RemoveField(
                    model_name='ordencompra',
                    name='fecha_emision',
                ),
                migrations.RemoveField(
                    model_name='ordencompra',
                    name='proveedor',
                ),
            ],
        ),
        # ── 0008_change_numero_unique_per_empresa ──
        # En prod esto nunca llegó a la BD (aplicada en falso): solo estado. Prod NO tiene unique (empresa, numero).
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='compra',
                    name='numero',
                    field=models.CharField(blank=True, max_length=20, null=True),
                ),
                migrations.AlterUniqueTogether(
                    name='compra',
                    unique_together={('empresa', 'numero')},
                ),
            ],
        ),
        # Defaults a nivel de BD que prod tiene (puestos fuera de las
        # migraciones). Solo BD; el estado de Django no los conoce.
        migrations.RunSQL(
            sql=(
                "ALTER TABLE compras_compra ALTER COLUMN moneda SET DEFAULT 'PEN'; "
                "ALTER TABLE compras_pagocompra ALTER COLUMN moneda SET DEFAULT 'PEN'; "
                "ALTER TABLE compras_ordencompra ALTER COLUMN proveedor_nombre SET DEFAULT ''; "
                "ALTER TABLE compras_compradetalle ALTER COLUMN created_at SET DEFAULT now(); "
                "ALTER TABLE compras_compradetalle ALTER COLUMN updated_at SET DEFAULT now(); "
                "ALTER TABLE compras_compradetalle ALTER COLUMN igv SET DEFAULT 0; "
                "ALTER TABLE compras_compradetalle ALTER COLUMN subtotal SET DEFAULT 0; "
                "ALTER TABLE compras_compradetalle ALTER COLUMN total SET DEFAULT 0;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        # ── 0009_fix_ordencompra_fecha_emision ──
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    # IF NOT EXISTS: en la BD legada la columna existe (0007 se
                    # aplicó en falso); en una BD limpia 0007 sí la elimina y hay
                    # que recrearla para que coincida con el modelo.
                    sql=(
                        "ALTER TABLE compras_ordencompra "
                        "ADD COLUMN IF NOT EXISTS fecha_emision date NOT NULL DEFAULT CURRENT_DATE; "
                        "ALTER TABLE compras_ordencompra "
                        "ALTER COLUMN fecha_emision SET DEFAULT CURRENT_DATE;"
                    ),
                    reverse_sql="ALTER TABLE compras_ordencompra ALTER COLUMN fecha_emision DROP DEFAULT;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='ordencompra',
                    name='fecha_emision',
                    field=models.DateField(default=datetime.date.today),
                ),
            ],
        ),
    ]
