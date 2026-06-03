import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Crea o actualiza el superusuario administrador para producción."

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from apps.empresas.models import Empresa

        User = get_user_model()

        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        nombre = os.environ.get("ADMIN_NOMBRE")
        apellido = os.environ.get("ADMIN_APELLIDO")

        missing = [name for name, val in {
            "ADMIN_EMAIL": email,
            "ADMIN_PASSWORD": password,
            "ADMIN_NOMBRE": nombre,
            "ADMIN_APELLIDO": apellido,
        }.items() if not val]

        if missing:
            raise CommandError(
                f"Faltan las siguientes variables de entorno: {', '.join(missing)}"
            )

        try:
            with transaction.atomic():
                empresa, empresa_created = Empresa.objects.get_or_create(
                    ruc="20603231717",
                    defaults={"nombre": "Soldigem"},
                )
                if empresa_created:
                    self.stdout.write(self.style.SUCCESS(f"Empresa creada: {empresa.nombre}"))
                else:
                    self.stdout.write(f"Empresa existente: {empresa.nombre}")

                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "nombre": nombre,
                        "apellido": apellido,
                        "is_staff": True,
                        "is_superuser": True,
                        "is_active": True,
                        "empresa": empresa,
                        "rol": "admin",
                    },
                )

                if user_created:
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"Superusuario creado: {email}")
                    )
                else:
                    user.nombre = nombre
                    user.apellido = apellido
                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True
                    user.empresa = empresa
                    user.rol = "admin"
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.WARNING(f"Superusuario actualizado: {email}")
                    )

        except Exception as exc:
            raise CommandError(f"Error al crear/actualizar el superusuario: {exc}") from exc
