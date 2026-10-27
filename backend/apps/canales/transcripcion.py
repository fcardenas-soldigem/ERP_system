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

    # MISMA configuración que el resto de la capa LLM (settings LLM_*): antes
    # leía VERTEX_PROJECT/VERTEX_LOCATION, que no existen → en prod el audio
    # iba sin proyecto, a otra región y con otro modelo.
    client = genai.Client(
        vertexai=True,
        project=getattr(settings, 'LLM_PROJECT', '') or None,
        location=getattr(settings, 'LLM_LOCATION', 'global') or 'global',
    )
    resp = client.models.generate_content(
        model=getattr(settings, 'LLM_MODEL', 'gemini-3.1-flash-lite'),
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
            _PROMPT,
        ],
    )
    texto = (resp.text or '').strip()
    logger.info('transcripcion ok: %d bytes → %d chars', len(audio_bytes), len(texto))
    return texto
