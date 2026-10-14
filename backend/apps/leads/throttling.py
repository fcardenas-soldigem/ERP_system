from rest_framework.throttling import AnonRateThrottle


class LeadAnonThrottle(AnonRateThrottle):
    """5 envíos por hora por IP. Scope independiente del resto de la API."""
    scope = 'leads'
    rate = '5/hour'
