from django.db import migrations

# Django 4.2 AddField(default=...) rellena las filas y luego DROPEA el default
# en Postgres. Las columnas NOT NULL nuevas quedan sin DEFAULT en BD, así que el
# código VIEJO (Cloud Run) revienta en cada INSERT que no las incluye.
#
# Esta migración restaura el DEFAULT a nivel de base de datos para las 3 columnas
# NOT NULL agregadas en Fase 1, de modo que los INSERT del código viejo sigan
# funcionando hasta el deploy del código nuevo.
#
# RunSQL con reverse_sql (DROP DEFAULT). No cambia el estado de Django (el modelo
# ya declara estos defaults); solo alinea el esquema físico.


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0018_backfill_detalleventa_origen'),
        ('empresas', '0007_soldigem_sin_stock'),
        ('inventario', '0011_producto_controla_stock'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE empresas_empresa ALTER COLUMN modo_inventario SET DEFAULT 'con_stock';",
            reverse_sql="ALTER TABLE empresas_empresa ALTER COLUMN modo_inventario DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE inventario_producto ALTER COLUMN controla_stock SET DEFAULT true;",
            reverse_sql="ALTER TABLE inventario_producto ALTER COLUMN controla_stock DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE ventas_detalleventa ALTER COLUMN stock_descontado SET DEFAULT false;",
            reverse_sql="ALTER TABLE ventas_detalleventa ALTER COLUMN stock_descontado DROP DEFAULT;",
        ),
    ]
