"""
Transcripción de audios de voz (A4): bytes .oga (Opus) → texto, con Gemini en
Vertex a través de la MISMA configuración del asistente (google-genai + ADC).

En tests SIEMPRE se mockea `transcribir` (nada sale de la máquina).
"""
import logging

logger = logging.getLogger(__name__)

_PROMPT = (
    'Transcribe literalmente este audio en español peruano de un vendedor. '
    'Devuelve SOLO el texto transcrito, sin comentarios.'
)


def transcribir(audio_bytes: bytes, mime: str = 'audio/ogg') -> str:
    from django.conf import settings
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=getattr(settings, 'VERTEX_PROJECT', None) or None,
        location=getattr(settings, 'VERTEX_LOCATION', 'us-central1'),
    )
    resp = client.models.generate_content(
        model=getattr(settings, 'LLM_MODELO_TRANSCRIPCION', 'gemini-2.0-flash'),
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
            _PROMPT,
        ],
    )
    texto = (resp.text or '').strip()
    logger.info('transcripcion ok: %d bytes → %d chars', len(audio_bytes), len(texto))
    return texto
