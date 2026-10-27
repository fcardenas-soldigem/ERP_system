from django.db import migrations

# Prod tiene DEFAULT gen_random_uuid() en empresas_empresa.uuid, puesto fuera de
# las migraciones. Se declara aquí para que una BD limpia (tests, entornos
# nuevos) tenga el MISMO esquema que prod. En prod es inocuo: vuelve a fijar
# el mismo default (solo metadatos, sin reescribir filas). El modelo sigue
# generando el uuid en Python; esto solo cubre INSERTs fuera del ORM.


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0008_alter_empresa_firma_aprobado_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE empresas_empresa ALTER COLUMN uuid SET DEFAULT gen_random_uuid();",
            reverse_sql=migrations.RunSQL.noop,   # prod ya lo tenía antes de esta migración
        ),
    ]
