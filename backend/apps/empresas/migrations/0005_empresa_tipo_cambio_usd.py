from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0004_add_firma_digital_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='tipo_cambio_usd',
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal('3.70'),
                help_text='Soles por cada dólar. Se usa para convertir montos en USD a PEN en reportes y dashboard.',
                max_digits=8,
                verbose_name='Tipo de cambio USD→PEN',
            ),
        ),
    ]
