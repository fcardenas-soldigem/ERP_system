from django.db import models

class Compra(models.Model):
    nombre = models.CharField(max_length=100)
    # Otros campos...

    def __str__(self):
        return self.nombre 