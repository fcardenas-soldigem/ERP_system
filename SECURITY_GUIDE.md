# Guía de Seguridad - Sistema ERP

## 🔒 Cambios de Seguridad Implementados

Este documento describe las mejoras de seguridad implementadas en el sistema ERP.

### ✅ Mejoras Implementadas

#### 1. Variables de Entorno para Secretos
- ❌ **ANTES**: Claves hardcodeadas en `settings.py`
- ✅ **AHORA**: Todas las claves sensibles en variables de entorno
  - `DJANGO_SECRET_KEY`: Clave secreta de Django
  - `JWT_SIGNING_KEY`: Clave de firmado de tokens JWT (separada)
  - `APIS_NET_PE_TOKEN`: Token de API externa

#### 2. Restricciones de CORS y Hosts
- ❌ **ANTES**: `CORS_ALLOW_ALL_ORIGINS=True` (inseguro)
- ✅ **AHORA**: Lista explícita de orígenes permitidos vía `CORS_ALLOWED_ORIGINS`
- ❌ **ANTES**: `ALLOWED_HOSTS='*'` (acepta cualquier dominio)
- ✅ **AHORA**: Validación de hosts permitidos, error si no se especifica en producción

#### 3. Headers de Seguridad Django
Activados en producción:
- ✅ `SESSION_COOKIE_SECURE=True`: Cookies solo por HTTPS
- ✅ `CSRF_COOKIE_SECURE=True`: Token CSRF solo por HTTPS
- ✅ `SESSION_COOKIE_HTTPONLY=True`: Previene acceso JS a cookies de sesión
- ✅ `CSRF_COOKIE_HTTPONLY=True`: Previene acceso JS a token CSRF
- ✅ `SECURE_HSTS_SECONDS=31536000`: HSTS por 1 año
- ✅ `SECURE_CONTENT_TYPE_NOSNIFF=True`: Previene MIME sniffing
- ✅ `X_FRAME_OPTIONS='DENY'`: Previene clickjacking
- ✅ `SECURE_REFERRER_POLICY`: Control de información del referrer

#### 4. Headers de Seguridad Nginx
Agregados al frontend:
- ✅ **Content-Security-Policy (CSP)**: Controla recursos que puede cargar la página
- ✅ **X-Frame-Options**: Previene clickjacking
- ✅ **X-Content-Type-Options**: Previene MIME sniffing
- ✅ **X-XSS-Protection**: Filtro XSS del navegador
- ✅ **Referrer-Policy**: Controla información del referrer
- ✅ **Permissions-Policy**: Restringe acceso a APIs del navegador
- ✅ **HSTS**: Fuerza HTTPS (comentado hasta configurar SSL)

#### 5. Tokens JWT Más Seguros
- ❌ **ANTES**: Access token válido por 1 día
- ✅ **AHORA**: Access token válido por 15 minutos
- ✅ Refresh token sigue siendo 7 días con rotación automática
- ✅ Blacklist activada tras rotación

#### 6. Contenedores No-Root
- ❌ **ANTES**: Contenedores ejecutándose como root (UID 0)
- ✅ **AHORA Backend**: Usuario `appuser` (UID 1000)
- ✅ **AHORA Frontend**: Usuario `nginx` (UID 101)
- ✅ Permisos mínimos necesarios en archivos

---

## 📋 Pasos de Configuración Requeridos

### 1. Generar Claves Seguras

Ejecuta estos comandos para generar claves criptográficamente seguras:

```bash
# Generar DJANGO_SECRET_KEY
python -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(50))"

# Generar JWT_SIGNING_KEY
python -c "import secrets; print('JWT_SIGNING_KEY=' + secrets.token_urlsafe(50))"
```

### 2. Crear Archivo .env

Copia el contenido de `ENV_EXAMPLE.txt` a:
- `/backend/.env` (para desarrollo local)
- Variables de entorno del sistema en producción (Cloud Run, Kubernetes, etc.)

```bash
# En la raíz del proyecto
cp ENV_EXAMPLE.txt backend/.env

# Edita el archivo con tus valores reales
nano backend/.env
```

### 3. Configurar Variables en Producción

**Para Google Cloud Run:**
```bash
gcloud run services update erp-backend \
  --set-env-vars "DJANGO_SECRET_KEY=tu-clave-aqui,JWT_SIGNING_KEY=otra-clave" \
  --set-env-vars "DJANGO_ALLOWED_HOSTS=tu-dominio.com" \
  --set-env-vars "CORS_ALLOWED_ORIGINS=https://tu-frontend.com"
```

**O usa Secret Manager (recomendado):**
```bash
# Crear secretos
echo -n "tu-clave-secreta" | gcloud secrets create django-secret-key --data-file=-
echo -n "tu-jwt-key" | gcloud secrets create jwt-signing-key --data-file=-

# Asociar al servicio
gcloud run services update erp-backend \
  --set-secrets "DJANGO_SECRET_KEY=django-secret-key:latest,JWT_SIGNING_KEY=jwt-signing-key:latest"
```

### 4. Actualizar Dominios

En `backend/config/settings.py`, actualiza:
```python
CSRF_TRUSTED_ORIGINS = [
    'https://tu-dominio-backend.com',
    'https://tu-dominio-frontend.com',
]
```

En `frontend/nginx.conf`, actualiza el CSP:
```nginx
add_header Content-Security-Policy "... connect-src 'self' https://tu-backend.com; ..." always;
```

### 5. Activar HSTS en Producción

Una vez que tengas HTTPS configurado, descomenta en `frontend/nginx.conf`:
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

---

## 🚀 Despliegue

### Desarrollo Local

```bash
# 1. Crear archivo .env con tus claves
cp ENV_EXAMPLE.txt backend/.env
# Edita backend/.env con valores reales

# 2. Levantar servicios
docker-compose up --build
```

### Producción

```bash
# 1. Configura todas las variables de entorno en tu plataforma cloud
# 2. Rebuild y redeploy de contenedores
docker build -t erp-backend -f backend/Dockerfile .
docker build -t erp-frontend -f frontend/Dockerfile .

# 3. Push y deploy según tu plataforma
```

---

## 🔍 Verificación de Seguridad

### Checklist de Producción

- [ ] Variables de entorno configuradas (no hardcodeadas)
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` configurado con dominios específicos
- [ ] `CORS_ALLOWED_ORIGINS` configurado con URLs específicas
- [ ] HTTPS habilitado en el load balancer/proxy
- [ ] HSTS activado en Nginx
- [ ] Contenedores corriendo como no-root
- [ ] Base de datos no expuesta públicamente
- [ ] Firewall/Security Groups configurados
- [ ] Backups automáticos habilitados
- [ ] Logs de seguridad monitoreados
- [ ] Rate limiting configurado

### Test de Headers

Verifica que los headers de seguridad estén activos:
```bash
# Test backend
curl -I https://tu-backend.com/api/

# Test frontend
curl -I https://tu-frontend.com/

# Busca estos headers:
# - Strict-Transport-Security
# - X-Frame-Options
# - X-Content-Type-Options
# - Content-Security-Policy
# - Referrer-Policy
```

---

## 🎯 Nivel de Seguridad Actual

**Antes de los cambios**: 4/10
**Después de los cambios**: 8/10 ✅

### Mejoras Adicionales Recomendadas (Futuro)

1. **Base de Datos**
   - [ ] Mover DB a red privada (VPC)
   - [ ] Conexión con TLS/SSL
   - [ ] Rotación automática de credenciales

2. **Rate Limiting**
   - [ ] Implementar throttling en DRF
   - [ ] Protección de login (django-axes)
   - [ ] WAF en el load balancer

3. **Monitoreo**
   - [ ] Logging estructurado de seguridad
   - [ ] Alertas de actividad sospechosa
   - [ ] Escaneo de vulnerabilidades (Snyk/Trivy)

4. **Autenticación**
   - [ ] 2FA para operaciones críticas
   - [ ] OAuth2/OIDC si integras terceros

5. **Archivos Subidos**
   - [ ] Antivirus en uploads (ClamAV)
   - [ ] Validación estricta de tipos de archivo
   - [ ] Almacenamiento en bucket separado

---

## 📞 Contacto de Seguridad

Si descubres una vulnerabilidad de seguridad, repórtala responsablemente a tu equipo de desarrollo.

**NO** compartas:
- Claves secretas
- Tokens de API
- Contraseñas de base de datos
- Archivos .env

Por ningún medio público (GitHub, chat, email no cifrado).

---

**Última actualización**: Octubre 2025
**Versión**: 1.0

