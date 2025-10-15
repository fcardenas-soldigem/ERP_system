# 🚀 Inicio Rápido - Configuración de Seguridad

## ⚡ 5 Pasos para Activar la Seguridad

### Paso 1: Generar Claves Seguras (2 minutos)

```bash
cd /Users/renatocardenas/Desktop/ERP/ERP_system
python3 generate_secrets.py
```

✅ Copia las claves generadas (las necesitarás en el siguiente paso)

---

### Paso 2: Crear Archivo .env (3 minutos)

```bash
# Crear el archivo .env en backend/
nano backend/.env
```

Pega este contenido y **reemplaza los valores** con los tuyos:

```bash
# === CLAVES GENERADAS (del paso 1) ===
DJANGO_SECRET_KEY=PEGA_AQUI_LA_CLAVE_GENERADA_EN_PASO_1
JWT_SIGNING_KEY=PEGA_AQUI_LA_OTRA_CLAVE_GENERADA_EN_PASO_1

# === BASE DE DATOS ===
DB_NAME=ERP_system
DB_USER=postgres
DB_PASSWORD=tu_password_seguro_de_postgres
DB_HOST=localhost
DB_PORT=5432

# === DJANGO SETTINGS ===
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# === CORS (Frontend) ===
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# === APIS EXTERNAS ===
APIS_NET_PE_TOKEN=tu_token_real_de_apis_net_pe

# === OPENAI (si lo usas) ===
OPENAI_API_KEY=tu_clave_openai
OPENAI_ASSISTANT_ID=asst_tu_id
OPENAI_MODEL=gpt-4

# === CLAUDE (si lo usas) ===
CLAUDE_API_KEY=tu_clave_claude
```

Guarda el archivo: `Ctrl+X`, luego `Y`, luego `Enter`

---

### Paso 3: Verificar Configuración (1 minuto)

```bash
python3 check_security.py
```

✅ Deberías ver "TODAS LAS VERIFICACIONES PASARON"  
❌ Si hay errores, corrige los items marcados con ❌

---

### Paso 4: Rebuild de Contenedores (5 minutos)

```bash
# Detener contenedores actuales
docker-compose down

# Rebuild con nueva configuración de seguridad
docker-compose up --build
```

---

### Paso 5: Verificar que Funciona (2 minutos)

Abre tu navegador:
- Backend: http://localhost:8080/admin
- Frontend: http://localhost:3000

✅ Si carga correctamente: ¡Listo! Tu sistema ahora es **8/10 en seguridad**

---

## 🆘 Problemas Comunes

### Error: "DJANGO_SECRET_KEY must be set"

**Causa:** No existe el archivo `.env` o está vacío  
**Solución:** Repite el Paso 2

### Error: "CORS_ALLOWED_ORIGINS must be set"

**Causa:** Falta configurar CORS en `.env`  
**Solución:** Agrega esta línea a `backend/.env`:
```bash
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Error: "ALLOWED_HOSTS must be set"

**Causa:** Falta configurar hosts permitidos  
**Solución:** Agrega esta línea a `backend/.env`:
```bash
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Los tokens JWT expiran muy rápido

**Causa:** Ahora duran 15 minutos (antes 1 día)  
**Solución:** Esto es intencional por seguridad. Usa el refresh token para renovarlos automáticamente.

---

## 📊 Qué Cambió en tu Sistema

### Antes (4/10) ❌
```python
SECRET_KEY = 'Rafaella0102!$11'  # Hardcodeado
CORS_ALLOW_ALL_ORIGINS = True     # Cualquiera puede acceder
ALLOWED_HOSTS = '*'                # Acepta todos los dominios
ACCESS_TOKEN_LIFETIME = 1 día      # Token válido 24h
# Sin headers de seguridad
# Contenedores como root
```

### Después (8/10) ✅
```python
SECRET_KEY = os.getenv('...')     # Variable de entorno
CORS_ALLOWED_ORIGINS = [lista]    # Solo dominios específicos
ALLOWED_HOSTS = [lista]            # Solo tus dominios
ACCESS_TOKEN_LIFETIME = 15 min     # Token válido 15 min
# 10+ headers de seguridad
# Contenedores como usuario sin privilegios
```

---

## 🎯 Para Producción (Cloud)

Cuando vayas a subir a la nube, sigue estos pasos adicionales:

### 1. Usar Secret Manager

**Google Cloud:**
```bash
# Crear secretos
echo -n "tu-clave" | gcloud secrets create django-secret --data-file=-

# Asociar al servicio
gcloud run services update erp-backend \
  --set-secrets "DJANGO_SECRET_KEY=django-secret:latest"
```

### 2. Configurar Dominios Reales

En tu Secret Manager o variables de entorno de producción:
```bash
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CORS_ALLOWED_ORIGINS=https://tudominio.com,https://www.tudominio.com
```

### 3. Actualizar nginx.conf

Descomenta la línea de HSTS (cuando tengas HTTPS):
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### 4. Actualizar settings.py

Modifica los CSRF_TRUSTED_ORIGINS con tus dominios reales:
```python
CSRF_TRUSTED_ORIGINS = [
    'https://tudominio.com',
    'https://www.tudominio.com',
]
```

---

## ✅ Checklist Final

Antes de considerar tu sistema seguro, verifica:

- [ ] ✅ Generé claves con `generate_secrets.py`
- [ ] ✅ Creé `backend/.env` con todas las variables
- [ ] ✅ `check_security.py` pasa todas las verificaciones
- [ ] ✅ `.env` está en `.gitignore`
- [ ] ✅ NO subí `.env` a Git
- [ ] ✅ Los contenedores se rebuildearon correctamente
- [ ] ✅ El sistema carga sin errores
- [ ] ✅ Guardé las claves en un gestor de contraseñas seguro

### Para producción adicionales:

- [ ] ⚠️ Moví las claves a Secret Manager del cloud
- [ ] ⚠️ Configuré dominios reales en `ALLOWED_HOSTS`
- [ ] ⚠️ Configuré URLs reales en `CORS_ALLOWED_ORIGINS`
- [ ] ⚠️ Activé HTTPS en el load balancer
- [ ] ⚠️ Descomentí HSTS en `nginx.conf`
- [ ] ⚠️ La base de datos está en red privada
- [ ] ⚠️ Configuré backups automáticos

---

## 📚 Más Información

- **Detalles completos:** `SECURITY_GUIDE.md`
- **Lista de cambios:** `CAMBIOS_SEGURIDAD.md`
- **Template variables:** `ENV_EXAMPLE.txt`

---

## 🎉 ¡Felicidades!

Tu sistema ERP ahora tiene:
- 🔐 Secretos protegidos
- 🚫 CORS restringido
- 🍪 Cookies seguras
- 🔒 Headers de seguridad
- ⏱️ Tokens de corta duración
- 👤 Contenedores no-root

**Calificación de Seguridad: 8/10** 🎯

---

*Última actualización: Octubre 2025*

