from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0009_add_inventarios_separados'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='marca',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='Marca',
            ),
        ),
    ]
