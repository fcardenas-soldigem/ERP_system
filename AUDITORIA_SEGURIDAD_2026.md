# AUDITORÍA DE SEGURIDAD ERP — Soldigem
**Fecha:** 2026-06-01  
**Auditor:** Claude Code (Sonnet 4.6) con skills /guard + /review + /health  
**Sistema:** ERP multi-tenant para PYMEs peruanas  
**Stack:** Django 4.2 + DRF + PostgreSQL (Supabase) · React 18 + Chakra UI · Google Cloud Run  
**Branch auditado:** `commit`

---

## CATEGORÍA 1 — AUTENTICACIÓN
**Puntaje: 5/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[CRÍTICO]** Sin protección brute force en `LoginView` — cualquier IP podía intentar contraseñas indefinidamente sin bloqueo. `backend/apps/authentication/views.py:14`
  - **CORREGIDO AUTOMÁTICAMENTE**: Se añadió rate limiting por IP (5 intentos → bloqueo 5 min) usando Django cache.

- **[CRÍTICO]** `BLACKLIST_AFTER_ROTATION: True` en settings.py pero `rest_framework_simplejwt.token_blacklist` NO estaba en `INSTALLED_APPS`. Los refresh tokens rotados no se invalidaban — reusables indefinidamente. `backend/config/settings.py:262`
  - **CORREGIDO AUTOMÁTICAMENTE**: Se añadió `rest_framework_simplejwt.token_blacklist` a INSTALLED_APPS. Ejecutar `python manage.py migrate` para activar.

- **[ALTO]** No existía endpoint de logout que invalide el refresh token. El logout era solo en el frontend (borrando localStorage).
  - **CORREGIDO AUTOMÁTICAMENTE**: Se creó `LogoutView` en `authentication/views.py` + ruta `POST /api/auth/logout/`.

- **[MEDIO]** `LoginView` expone `str(e)` en errores 500, filtrando mensajes internos de Django/Python.
  - **CORREGIDO AUTOMÁTICAMENTE**: El nuevo LoginView no propaga excepciones internas al cliente.

- **[BUENO]** ACCESS_TOKEN_LIFETIME = 15 minutos ✓  
- **[BUENO]** JWT_SIGNING_KEY separado de DJANGO_SECRET_KEY, ambos desde env vars ✓  
- **[BUENO]** Password validators (similitud, longitud, comunes, numérico) ✓  
- **[BUENO]** ROTATE_REFRESH_TOKENS = True ✓  

---

## CATEGORÍA 2 — MULTI-TENANT / AISLAMIENTO DE DATOS
**Puntaje: 3/10**  
**Estado: ❌ CRÍTICO**

### Hallazgos:

- **[CRÍTICO]** `EmpresaViewSet` devuelve `Empresa.objects.all()` sin filtro por empresa del usuario. Cualquier usuario autenticado podía listar, leer y modificar datos de TODAS las empresas del sistema. `backend/apps/core/views.py:22`
  - **CORREGIDO AUTOMÁTICAMENTE**: Se añadió `get_queryset()` que limita a la empresa del usuario (superusers ven todas).

- **[CRÍTICO]** `UsuarioViewSet` devuelve `Usuario.objects.all()` — exposición de usuarios de otras empresas. `backend/apps/core/views.py:27`
  - **CORREGIDO AUTOMÁTICAMENTE**: Filtrado por empresa.

- **[CRÍTICO]** `PerfilViewSet` devuelve `Perfil.objects.all()` — misma vulnerabilidad. `backend/apps/core/views.py:32`
  - **CORREGIDO AUTOMÁTICAMENTE**: Filtrado por empresa.

- **[ALTO]** `MessageViewSet` en ai_assistant filtra solo por `conversation_id` sin verificar que la conversación pertenezca a la empresa del usuario. Si un usuario conoce el ID de una conversación de otra empresa, puede leer sus mensajes. `backend/apps/ai_assistant/views.py:41-43`
  - **PENDIENTE MANUAL**: Agregar filtro `conversation__empresa=request.user.empresa`.

- **[BUENO]** `VentaViewSet`, `ClienteViewSet`, `CompraViewSet`, `ProveedorViewSet` correctamente filtrados ✓  
- **[BUENO]** `GuiaRemisionViewSet`, `ProductoViewSet`, `AlmacenViewSet` filtrados ✓  
- **[BUENO]** Importador Excel: todo scoped a la empresa del usuario ✓  
- **[NOTA]** `VentaListCreateView` y `VentaRetrieveUpdateDestroyView` tienen `Venta.objects.all()` en lines 44-49 pero estas clases son **código muerto** — no están registradas en `ventas/urls.py`. Riesgo latente si se conectan en el futuro.

---

## CATEGORÍA 3 — VALIDACIÓN DE INPUTS
**Puntaje: 7/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[BUENO]** Django ORM usado en 100% de las consultas — SQL injection imposible ✓  
- **[BUENO]** Importador valida extensión de archivo (.xlsx, .xls, .csv) ✓  
- **[BUENO]** Importación de clientes valida: DNI (8 dígitos), RUC (11 dígitos), teléfono (9 dígitos), email con regex ✓  
- **[BUENO]** `_safe_decimal` en importador maneja valores maliciosos sin lanzar excepciones ✓  
- **[BUENO]** password es `write_only=True` en `LoginSerializer` ✓  

- **[MEDIO]** Sin límite de tamaño de archivo en el importador Excel. Un archivo de 500 MB podría agotar memoria del servidor. `backend/apps/importador/views.py:35`
  - **CORREGIDO AUTOMÁTICAMENTE**: Límite de 10 MB implementado.

- **[MEDIO]** DRF no sanitiza HTML/JS en campos de texto por defecto. Campos como `nombre`, `descripcion`, `notas` aceptan `<script>alert(1)</script>`. El riesgo es bajo si el frontend escapa correctamente, pero no hay defensa en backend.
  - **PENDIENTE MANUAL**: Añadir un validador de campo que rechace tags HTML en campos de texto sensibles.

- **[MEDIO]** Errores de fila en importador incluyen `str(exc)[:300]` con posibles mensajes internos de Django ORM (ej. constraint violations que revelan estructura de BD).

---

## CATEGORÍA 4 — EXPOSICIÓN DE DATOS SENSIBLES
**Puntaje: 4/10**  
**Estado: ❌ CRÍTICO**

### Hallazgos:

- **[CRÍTICO]** `erp_backup.sql` está rastreado en git (`git ls-files` confirma). Este archivo SQL puede contener datos reales de clientes, RUCs, precios, credenciales hasheadas. `./erp_backup.sql`
  - **CORREGIDO AUTOMÁTICAMENTE**: Añadido `erp_backup.sql` y `*_backup.sql` al `.gitignore`.
  - **PENDIENTE MANUAL URGENTE**: Ejecutar `git rm --cached erp_backup.sql` y hacer un nuevo commit para removerlo del historial. Si contiene datos reales, considerar `git filter-branch` o BFG Repo Cleaner.

- **[ALTO]** Múltiples views exponen `str(e)` en respuestas 500, filtrando mensajes internos:
  - `compras/views.py` — varios endpoints
  - `ventas/views.py:248` — importador clientes
  - `core/views.py:64` — UsuarioPermisosView (antes de corrección)
  - **PENDIENTE MANUAL**: Reemplazar `str(e)` por mensajes genéricos en producción.

- **[BUENO]** `SECRET_KEY` y `JWT_SIGNING_KEY` desde env vars ✓  
- **[BUENO]** `.env`, `backend/.env`, `frontend/.env` NO están rastreados en git ✓  
- **[BUENO]** `DEBUG=False` en producción (settings lee DJANGO_DEBUG env var, default False) ✓  
- **[BUENO]** `UserSerializer` NO expone password hash, tokens internos ni datos sensibles ✓  
- **[BUENO]** Logging en nivel WARNING en producción — no registra datos sensibles ✓  
- **[BUENO]** `password` es `write_only=True` en serializers ✓  

---

## CATEGORÍA 5 — SEGURIDAD HTTP Y HEADERS
**Puntaje: 8/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[BUENO]** HSTS: 31,536,000 segundos + includeSubDomains + preload ✓  
- **[BUENO]** X_FRAME_OPTIONS = 'DENY' (anti-clickjacking) ✓  
- **[BUENO]** SECURE_CONTENT_TYPE_NOSNIFF = True ✓  
- **[BUENO]** CORS: restringido a orígenes explícitos (falla en startup si no está configurado) ✓  
- **[BUENO]** CSRF_COOKIE_SECURE + SESSION_COOKIE_SECURE = True en producción ✓  
- **[BUENO]** SESSION_COOKIE_HTTPONLY = True ✓  
- **[BUENO]** CSRF_COOKIE_SAMESITE = 'Lax' ✓  
- **[BUENO]** SECURE_PROXY_SSL_HEADER configurado para Cloud Run ✓  
- **[BUENO]** `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'` ✓  

- **[MEDIO]** Sin Content-Security-Policy (CSP) header. No hay middleware de CSP configurado en settings.py ni en ningún proxy/nginx. Sin CSP, XSS potenciales tienen más impacto.
  - **PENDIENTE MANUAL**: Instalar `django-csp` y configurar una política restrictiva.

- **[BAJO]** `SECURE_SSL_REDIRECT` está comentado (línea 54 settings.py). Cloud Run maneja HTTPS pero si alguna vez se sirve directamente Django, HTTP quedaría expuesto.

---

## CATEGORÍA 6 — PERMISOS Y RBAC
**Puntaje: 7/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[BUENO]** Sistema de roles implementado: admin, comercial, produccion, almacen, contador, readonly, personalizado ✓  
- **[BUENO]** `ModulePermission` con `ROLE_PERMISSIONS` granular por módulo y método HTTP ✓  
- **[BUENO]** `HasEmpresaPermission` aplicado en la mayoría de ViewSets ✓  
- **[BUENO]** Rol 'personalizado' con `PermisoUsuario` para permisos a nivel de campo ✓  
- **[BUENO]** Superusuarios tienen acceso completo, control adecuado ✓  

- **[ALTO]** `ConversationViewSet` y `MessageViewSet` en ai_assistant no declaran `permission_classes` — heredan el default de REST_FRAMEWORK (`IsAuthenticated`) pero no verifican empresa ni rol. `backend/apps/ai_assistant/views.py:27,37`
  - **PENDIENTE MANUAL**: Agregar `permission_classes = [IsAuthenticated, HasEmpresaPermission]`.

- **[MEDIO]** Módulos `guias`, `servicios`, `finanzas` no están en el `MODULE_MAP` de `ModulePermission`. El método `_resolve_module` devuelve `None` para estos módulos, lo que resulta en `return True` (línea 131) — acceso permitido a cualquier rol. `backend/apps/core/permissions.py:130-131`
  - **PENDIENTE MANUAL**: Añadir 'guias', 'servicios', 'finanzas' al MODULE_MAP y a ROLE_PERMISSIONS.

- **[MEDIO]** Importador: vistas solo usan `IsAuthenticated` sin verificar si el rol tiene permiso de importación. Cualquier usuario autenticado puede importar datos masivamente.
  - **PENDIENTE MANUAL**: Agregar `ModulePermission` al importador o crear permiso específico para importación.

---

## CATEGORÍA 7 — SEGURIDAD DEL FRONTEND
**Puntaje: 2/10**  
**Estado: ❌ CRÍTICO**

### Hallazgos:

- **[CRÍTICO]** JWT access_token y refresh_token almacenados en `localStorage`. XSS en cualquier parte de la app (incluyendo dependencias npm comprometidas) puede exfiltrar ambos tokens. `frontend/src/lib/api.js:14,43`
  - **PENDIENTE MANUAL**: Migrar a httpOnly cookies. El backend debe emitir tokens via Set-Cookie con `HttpOnly; Secure; SameSite=Strict`. Requiere cambio arquitectónico significativo.

- **[MEDIO]** `empresa_id` también en localStorage. Un atacante XSS puede manipular la empresa activa del usuario. `frontend/src/lib/api.js:59`

- **[BAJO]** `console.error()` con datos de respuesta del servidor en al menos 3 lugares (`api.js:163`, `api.js:190`, `api.js:213`). En producción, los DevTools muestran estos errores que podrían contener datos de usuario.
  - **PENDIENTE MANUAL**: Remover console.log/error en producción (usar variable de entorno VITE_NODE_ENV).

- **[BUENO]** Logout limpia todos los tokens de localStorage y redirige a /login ✓  
- **[BUENO]** Rutas protegidas: `checkAuth()` redirige al login si no hay token válido ✓  
- **[BUENO]** No hay datos sensibles en query params de URL ✓  
- **[BUENO]** Token no se muestra en la UI ✓  

---

## CATEGORÍA 8 — SEGURIDAD DEL IMPORTADOR EXCEL
**Puntaje: 8/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[BUENO]** Validación de extensión: solo .xlsx, .xls, .csv aceptados ✓  
- **[BUENO]** Archivos procesados en memoria con pandas/openpyxl — nunca ejecutados ✓  
- **[BUENO]** Todo dato importado scoped a `self.empresa` del usuario ✓  
- **[BUENO]** Todos los lookups (almacén, categoría, cliente) filtran por empresa ✓  
- **[BUENO]** Django maneja el almacenamiento de archivo — sin path traversal ✓  
- **[BUENO]** Datos pasan por helpers `_safe_decimal`, `_safe_date` sin evaluación de código ✓  

- **[MEDIO]** Sin límite de tamaño en `UploadView`. `backend/apps/importador/views.py:35`
  - **CORREGIDO AUTOMÁTICAMENTE**: Límite de 10 MB implementado.

- **[BAJO]** Errores de fila incluyen `str(exc)[:300]` que puede revelar mensajes ORM internos.

---

## CATEGORÍA 9 — GENERACIÓN DE PDFs
**Puntaje: 9/10**  
**Estado: ✅ APROBADO**

### Hallazgos:

- **[BUENO]** PDFs generados desde objetos ya filtrados por empresa (cotización/guía pertenecen al usuario) ✓  
- **[BUENO]** ReportLab opera completamente en memoria — sin archivos temporales ✓  
- **[BUENO]** `nombre_archivo` en guias usa regex `re.sub(r'[^\w\s-]', '', ...)` para sanitizar — sin path traversal ✓  
- **[BUENO]** Todos los campos del PDF provienen del ORM — no hay interpolación directa de input del usuario ✓  
- **[BUENO]** Sin metadata de rutas del servidor en el PDF ✓  

- **[BAJO]** El logo de empresa se carga desde `empresa.logo.path`. Si un administrador malicioso sube un archivo con extensión .png pero contenido diferente, ReportLab puede fallar con un error pero no ejecuta código. Riesgo mínimo pero falta validación de tipo MIME real del logo.

---

## CATEGORÍA 10 — AUDITORÍA Y LOGS
**Puntaje: 4/10**  
**Estado: ⚠️ OBSERVACIONES**

### Hallazgos:

- **[BUENO]** LOGGING configurado en WARNING para producción — no filtra datos sensibles ✓  
- **[BUENO]** Errores HTTP 500 de Django se loggean en `django.request` logger ✓  
- **[BUENO]** `ImportService` registra compras/ventas creadas en logger.info ✓  

- **[ALTO]** Sin logging estructurado de login/logout. Después de corrección, se añadió `logger.info` y `logger.warning` en LoginView/LogoutView, pero no había antes.
  - **CORREGIDO PARCIALMENTE**: LoginView ahora loggea intentos exitosos y fallidos.

- **[ALTO]** Sin audit trail de cambios de estado (ventas, compras, guías). No hay registro de quién cambió qué y cuándo en transacciones críticas.
  - **PENDIENTE MANUAL**: Implementar modelo `AuditLog` o usar `django-simple-history`.

- **[ALTO]** Sin logging de importaciones Excel por usuario. No hay forma de saber qué usuario importó qué y cuándo desde los logs.
  - **PENDIENTE MANUAL**: Añadir log estructurado en `ImportService.run()`.

- **[MEDIO]** Sin log de cambios de precios de productos. Las modificaciones de precio no dejan rastro.

- **[MEDIO]** Los errores en `except Exception as e` en muchas vistas solo hacen `raise` sin logging — los errores se pierden o van a log genérico sin contexto.

---

## REPORTE FINAL

```
╔════════════════════════════════════════════╗
║         REPORTE DE SEGURIDAD ERP           ║
║              Soldigem · 2026               ║
╠════════════════════════════════════════════╣
║ Categoría 1  Autenticación        5/10     ║
║ Categoría 2  Multi-tenant         3/10     ║
║ Categoría 3  Validación inputs    7/10     ║
║ Categoría 4  Datos sensibles      4/10     ║
║ Categoría 5  Headers HTTP         8/10     ║
║ Categoría 6  Permisos RBAC        7/10     ║
║ Categoría 7  Frontend             2/10     ║
║ Categoría 8  Importador Excel     8/10     ║
║ Categoría 9  Generación PDFs      9/10     ║
║ Categoría 10 Auditoría y Logs     4/10     ║
╠════════════════════════════════════════════╣
║  PUNTUACIÓN TOTAL:       57/100            ║
║  NIVEL:  BAJO — Vulnerabilidades graves    ║
╚════════════════════════════════════════════╝
```

**Escala:**
- 0-60: BAJO — vulnerabilidades graves pendientes  ← **AQUÍ**
- 61-75: MEDIO — mejoras importantes necesarias
- 76-89: ALTO — sistema seguro con observaciones menores
- 90-100: EXCELENTE — listo para producción

---

## TOP 3 RIESGOS MÁS URGENTES

1. **[RIESGO MÁXIMO] JWT tokens en localStorage** — Un XSS en cualquier componente React o dependencia npm puede exfiltrar `access_token` + `refresh_token`, dando acceso completo a la cuenta del usuario. Con tokens válidos (refresh: 7 días), el atacante mantiene acceso hasta que el usuario cambie contraseña. Requiere migrar a httpOnly cookies.

2. **[RIESGO ALTO] `erp_backup.sql` en historial git** — El archivo de backup SQL está rastreado en git desde el commit `4beb0a2`. Contiene datos reales de la BD (clientes, facturas, RUCs, precios, hashes de contraseñas). Cualquier persona con acceso al repositorio tiene acceso a todos estos datos. Requiere `git rm --cached erp_backup.sql` + rewrite del historial con BFG si el repo es compartido.

3. **[RIESGO ALTO] EmpresaViewSet/UsuarioViewSet sin filtro de empresa (pre-corrección)** — Cualquier usuario autenticado podía listar y modificar datos de todas las empresas via `/api/core/empresas/`. Esto permitía cross-company data access y privilege escalation. **Ya corregido** pero el fix necesita ser desplegado urgentemente.

---

## CORRECCIONES APLICADAS AUTOMÁTICAMENTE

| # | Archivo | Corrección |
|---|---------|-----------|
| 1 | `.gitignore` | Añadido `erp_backup.sql` y `*_backup.sql` |
| 2 | `backend/apps/core/views.py` | EmpresaViewSet, UsuarioViewSet, PerfilViewSet filtran por empresa del usuario |
| 3 | `backend/config/settings.py` | Añadido `rest_framework_simplejwt.token_blacklist` a INSTALLED_APPS |
| 4 | `backend/apps/authentication/views.py` | Rate limiting brute force (5 intentos → 5 min bloqueo) |
| 5 | `backend/apps/authentication/views.py` | LogoutView que invalida refresh token en blacklist |
| 6 | `backend/apps/authentication/urls.py` | Endpoint `POST /api/auth/logout/` registrado |
| 7 | `backend/apps/importador/views.py` | Límite de 10 MB en subida de archivos Excel |

---

## CORRECCIONES MANUALES REQUERIDAS (PRIORIZADAS)

### URGENTE (antes del próximo deploy)

1. **Ejecutar `python manage.py migrate`** para crear tablas del token blacklist.

2. **Remover `erp_backup.sql` del historial git:**
   ```bash
   git rm --cached erp_backup.sql
   git commit -m "security: remove SQL backup from git tracking"
   # Si el repo es compartido y el backup tiene datos reales:
   # Usar BFG Repo Cleaner para rewrite del historial
   ```

3. **Fix `MessageViewSet` en ai_assistant** — agregar filtro por empresa:
   ```python
   def get_queryset(self):
       conversation_id = self.kwargs.get('conversation_pk')
       return Message.objects.filter(
           conversation_id=conversation_id,
           conversation__empresa=self.request.user.empresa
       )
   ```

### ALTA PRIORIDAD (sprint actual)

4. **Migrar JWT de localStorage a httpOnly cookies** en el frontend. El backend debe configurar:
   ```python
   # En LoginView: en lugar de devolver token en body
   response = Response({'user': user_data})
   response.set_cookie('access_token', str(refresh.access_token),
       httponly=True, secure=True, samesite='Strict', max_age=900)
   response.set_cookie('refresh_token', str(refresh),
       httponly=True, secure=True, samesite='Strict', max_age=604800)
   return response
   ```

5. **Añadir guias/servicios/finanzas al MODULE_MAP** en `core/permissions.py`:
   ```python
   MODULE_MAP = {
       ...
       'guia': 'guias',
       'servicio': 'servicios',
       'finanza': 'finanzas',
   }
   ```
   Y añadir permisos por rol en `ROLE_PERMISSIONS`.

6. **Agregar `ModulePermission` a importador** y ai_assistant views.

### PRIORIDAD MEDIA (próximo sprint)

7. **Instalar django-csp** para Content-Security-Policy:
   ```bash
   pip install django-csp
   # settings.py: añadir 'csp.middleware.CSPMiddleware' al MIDDLEWARE
   ```

8. **Implementar audit trail** — instalar `django-simple-history` o crear modelo `AuditLog` con: usuario, empresa, acción, modelo, instancia_id, valores_anteriores, valores_nuevos, timestamp.

9. **Remover `console.error` en producción** — usar variable de entorno:
   ```javascript
   if (import.meta.env.PROD) {
     // no console.error with sensitive data
   }
   ```

10. **Validar tipo MIME real de logos** en PDF generator — usar python-magic para confirmar que el archivo es realmente una imagen.

11. **Limpiar código muerto** — eliminar `VentaListCreateView` y `VentaRetrieveUpdateDestroyView` de `ventas/views.py` (líneas 43-50) para evitar que sean conectados accidentalmente.

12. **Reemplazar `str(e)` en respuestas 500** — usar mensajes genéricos en producción:
    ```python
    except Exception:
        logger.exception('Error inesperado en <vista>')
        return Response({'error': 'Error interno del servidor'}, status=500)
    ```

---

## HEALTH DASHBOARD (código)

```
CODE HEALTH — Seguridad
========================
Proyecto: ERP_system
Fecha:    2026-06-01
Branch:   commit

Categoría         Score   Estado
─────────────     ─────   ──────────
Autenticación      5/10   NEEDS WORK
Multi-tenant       3/10   CRITICAL
Input validation   7/10   WARNING
Datos sensibles    4/10   NEEDS WORK
HTTP Headers       8/10   WARNING
RBAC               7/10   WARNING
Frontend           2/10   CRITICAL
Importador Excel   8/10   WARNING
PDFs               9/10   CLEAN
Auditoría/Logs     4/10   NEEDS WORK

SCORE COMPUESTO: 57/100 — BAJO
```

---

*Generado por Claude Code (Sonnet 4.6) · Skills: /guard + /review + /health · 2026-06-01*
