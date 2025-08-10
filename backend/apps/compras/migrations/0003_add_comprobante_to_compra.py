from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0002_add_timestamps_to_pagocompra'),
    ]

    operations = [
        migrations.AddField(
            model_name='compra',
            name='comprobante',
            field=models.FileField(blank=True, null=True, upload_to='comprobantes/compras/'),
        ),
    ] 