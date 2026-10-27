import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    fecha_emision exists in the DB (from 0001_initial) as NOT NULL with no default,
    but was accidentally removed from the model without a migration.
    SeparateDatabaseAndState lets us:
      - Tell Django's state tracker that the field exists (AddField in state_operations)
      - Add a DB-level default to the existing column so inserts always succeed
        even if the ORM value is somehow absent (database_operations RunSQL)
    """

    dependencies = [
        ('compras', '0008_change_numero_unique_per_empresa'),
    ]

    operations = [
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
