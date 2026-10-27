from django.db import migrations

# No-op histórico. 0001_initial ya crea created_at/updated_at en PagoCompra
# (el initial se regeneró incluyéndolos), así que los AddField que vivían aquí
# rompían `migrate` en una BD limpia ("column created_at ... already exists").
# El archivo se conserva vacío para que las BDs que ya lo tienen aplicado
# mantengan su historial intacto.


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
    ]

    operations = []
