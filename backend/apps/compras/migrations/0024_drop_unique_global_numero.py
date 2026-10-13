from django.db import migrations


class Migration(migrations.Migration):
    """
    Elimina el UNIQUE GLOBAL sobre compras_compra.numero — drift de BD que el
    modelo nunca declaró (el modelo tiene unique_together ['empresa','numero'],
    que es lo correcto en multitenant y lo que ya hace Venta).

    El constraint global hacía imposible que dos empresas tuvieran su propia
    C-000001: registrar-factura devolvía 500 (UniqueViolation) en cuanto una
    segunda empresa generaba su primera compra. Detectado en QA del flujo
    cotización → OC → factura.
    """

    dependencies = [
        ('compras', '0023_backfill_totales_oc'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE compras_compra DROP CONSTRAINT IF EXISTS compras_compra_numero_key;",
            reverse_sql="ALTER TABLE compras_compra ADD CONSTRAINT compras_compra_numero_key UNIQUE (numero);",
        ),
    ]
