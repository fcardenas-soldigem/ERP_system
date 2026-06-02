from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """
    Agrega Content-Security-Policy y headers de seguridad relacionados
    a todas las respuestas HTTP. En DEBUG usa directivas permisivas para
    que Vite HMR funcione; en producción aplica política estricta.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if settings.DEBUG:
            script_src = "'self' 'unsafe-inline' 'unsafe-eval'"
            connect_src = "'self' http://localhost:* ws://localhost:* wss://localhost:*"
        else:
            script_src = "'self'"
            connect_src = "'self'"

        csp_directives = [
            "default-src 'self'",
            f"script-src {script_src}",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob:",
            f"connect-src {connect_src}",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
        ]

        response['Content-Security-Policy'] = '; '.join(csp_directives)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response
