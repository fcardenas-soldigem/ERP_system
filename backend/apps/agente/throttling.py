"""Rate limit del MCP: por TOKEN (no por IP). El agente sale de IPs de Anthropic."""
from rest_framework.throttling import SimpleRateThrottle

from .models import ApiToken


class MCPTokenThrottle(SimpleRateThrottle):
    scope = 'mcp'  # rate en DEFAULT_THROTTLE_RATES (settings): '60/min'

    def get_cache_key(self, request, view):
        token = getattr(request, 'auth', None)
        if not isinstance(token, ApiToken):
            return None  # sin token válido no se throttlea (el permiso ya da 401)
        return self.cache_format % {'scope': self.scope, 'ident': token.pk}
