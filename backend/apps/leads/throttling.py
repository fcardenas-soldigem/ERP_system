from rest_framework.throttling import AnonRateThrottle


def client_ip(request):
    """
    IP real del visitante detrás de proxies (Vercel → Google Front End → Cloud Run).

    En producción el POST llega así:
        visitante → Vercel (rewrite) → Google Front End → Cloud Run → Django

    El edge (Vercel) reescribe el header ``X-Forwarded-For`` con la IP real del
    visitante como PRIMER valor de la cadena; los valores siguientes son los
    proxies (Vercel egress, GFE), cuyas IPs **rotan** entre peticiones. Por eso
    tomamos el primer valor (el visitante) y no ``REMOTE_ADDR`` (que es el proxy
    inmediato de Google) ni la cadena completa.

    Supuesto de confianza: el borde que mira al público (Vercel) sanea el XFF
    entrante. Si Cloud Run quedara accesible por su URL ``*.run.app`` sin pasar
    por Vercel, un atacante podría falsificar este primer valor; por eso conviene
    restringir el ingress de Cloud Run al borde (ver nota en DEPLOY.md).
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        # Primer valor = visitante; el resto son los proxies de la cadena.
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LeadAnonThrottle(AnonRateThrottle):
    """
    5 envíos por hora por IP de visitante. Scope independiente del resto de la API.

    DRF por defecto (``NUM_PROXIES=None``) identifica al cliente con la cadena
    ``X-Forwarded-For`` **completa**. Detrás de Vercel/Cloud Run eso mezcla la IP
    del visitante con las de los proxies (que rotan), de modo que:
      - un mismo visitante obtiene claves distintas cuando rota el proxy → el
        límite de 5/hora se evade, y
      - el conteo deja de ser "por visitante".

    Forzamos la identidad a la IP del visitante (``client_ip``) para que:
      - visitantes distintos NO se bloqueen entre sí, y
      - un mismo visitante SÍ quede limitado a 5/hora aunque roten los proxies.

    Misma fuente de verdad que ``apps.leads.views._client_ip`` → la IP guardada
    en el Lead y la usada para el throttle no se desincronizan.
    """
    scope = 'leads'
    rate = '5/hour'

    def get_ident(self, request):
        return client_ip(request)
