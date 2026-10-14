from django.db import models


class Lead(models.Model):
    """
    Lead de acceso anticipado capturado desde la landing pública.
    No es multitenant: vive fuera de 'empresa' (son prospectos, no clientes).
    """
    TAMANO_CHOICES = [
        ('1-5', '1 a 5 personas'),
        ('6-20', '6 a 20 personas'),
        ('21-50', '21 a 50 personas'),
        ('50+', 'Más de 50 personas'),
    ]

    nombre = models.CharField(max_length=120)
    empresa = models.CharField(max_length=160, blank=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    rubro = models.CharField(max_length=120, blank=True)
    tamano = models.CharField(max_length=10, choices=TAMANO_CHOICES, blank=True)
    usa_inventario = models.BooleanField(null=True, blank=True)
    mensaje = models.TextField(blank=True)

    # Atribución de campaña (UTM) — de dónde vino el lead.
    utm_source = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=120, blank=True)

    # Metadatos de captura (no se muestran al usuario).
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.nombre} — {self.empresa or self.email}'
