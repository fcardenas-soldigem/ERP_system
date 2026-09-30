from django.db import migrations

# H2 — Soldigem opera en modo back-to-back (sin inventario).
RUC_SOLDIGEM = '20603231717'


def set_soldigem_sin_stock(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    # Idempotente: filtra por RUC y actualiza (0 o 1 fila).
    Empresa.objects.filter(ruc=RUC_SOLDIGEM).update(modo_inventario='sin_stock')


def revert(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    Empresa.objects.filter(ruc=RUC_SOLDIGEM).update(modo_inventario='con_stock')


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0006_empresa_modo_inventario'),
    ]

    operations = [
        migrations.RunPython(set_soldigem_sin_stock, revert),
    ]
