from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagocompra',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='pagocompra',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ] 