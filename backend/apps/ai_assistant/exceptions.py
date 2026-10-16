"""Excepciones del asistente IA que las vistas traducen a respuestas útiles."""


class AsistenteIANoConfigurado(Exception):
    """Falta OPENAI_API_KEY (o está vacía) en el entorno del servidor.

    No es un error del usuario ni un bug: es configuración del despliegue
    (secreto no inyectado en la revisión). Las vistas la devuelven como 503 con
    un mensaje claro, en lugar de un 500 genérico que dispara la alerta de 5xx
    y no dice qué falta.
    """

    mensaje = (
        'El asistente de IA no está configurado en este servidor. '
        'Contacta al administrador.'
    )

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)
