from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cotizaciones', '0002_cotizacion_pago_facturas'),
    ]

    operations = [
        migrations.AddField(
            model_name='cotizacion',
            name='precios_incluyen_igv',
            field=models.BooleanField(
                default=False,
                help_text='True si los precios ingresados ya incluyen IGV (se extrae). False si los precios no incluyen IGV (se agrega).'
            ),
        ),
    ]
