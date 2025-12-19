# 🏗️ ARQUITECTURA TÉCNICA DEL SISTEMA ERP

**Documento Complementario a la Documentación Completa**

---

## 📊 DIAGRAMAS DE ARQUITECTURA

### 1. Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              React Frontend (Port 3000)               │  │
│  │  • Chakra UI  • React Router  • Axios  • Recharts    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE NEGOCIO                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Django REST API (Port 8080)                 │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  Authentication  │  Ventas  │  Compras         │  │  │
│  │  │  Inventario      │  ML      │  Cotizaciones    │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  Servicios:                                     │  │  │
│  │  │  • JWT Auth  • ML Training  • PDF Generation   │  │  │
│  │  │  • Data Extraction  • OpenAI Integration       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ SQL
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PERSISTENCIA                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         PostgreSQL Database (Port 5432)              │  │
│  │  • Tablas relacionales  • Índices  • Constraints    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Sistema de Archivos                      │  │
│  │  • Media (logos, PDFs)  • ML Models (pickles)       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. FLUJO DE AUTENTICACIÓN JWT

```
┌─────────┐                                    ┌─────────┐
│ Cliente │                                    │ Backend │
└────┬────┘                                    └────┬────┘
     │                                              │
     │ 1. POST /api/token/                          │
     │    {username, password}                      │
     ├─────────────────────────────────────────────>│
     │                                              │
     │                              2. Validar      │
     │                                 credenciales │
     │                                              │
     │ 3. {access_token, refresh_token}             │
     │<─────────────────────────────────────────────┤
     │                                              │
     │ 4. GET /api/ventas/                          │
     │    Header: Authorization: Bearer <access>    │
     ├─────────────────────────────────────────────>│
     │                                              │
     │                              5. Validar JWT  │
     │                                 Verificar    │
     │                                 empresa      │
     │                                              │
     │ 6. {ventas: [...]}                           │
     │<─────────────────────────────────────────────┤
     │                                              │
     │ [Access token expira después de 5 min]      │
     │                                              │
     │ 7. POST /api/token/refresh/                  │
     │    {refresh: <refresh_token>}                │
     ├─────────────────────────────────────────────>│
     │                                              │
     │ 8. {access: <new_access_token>}              │
     │<─────────────────────────────────────────────┤
     │                                              │
```

---

## 3. FLUJO DE CREACIÓN DE COTIZACIÓN

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│ Frontend │          │  Backend │          │    BD    │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                      │
     │ 1. Cargar datos     │                      │
     │    iniciales        │                      │
     ├────────────────────>│                      │
     │                     │ 2. GET clientes,     │
     │                     │    productos,        │
     │                     │    empresa           │
     │                     ├─────────────────────>│
     │                     │                      │
     │                     │ 3. Datos             │
     │                     │<─────────────────────┤
     │ 4. Datos            │                      │
     │<────────────────────┤                      │
     │                     │                      │
     │ 5. Usuario llena    │                      │
     │    formulario       │                      │
     │                     │                      │
     │ 6. POST /api/       │                      │
     │    cotizaciones/    │                      │
     │    {datos}          │                      │
     ├────────────────────>│                      │
     │                     │ 7. Validar datos     │
     │                     │    Generar número    │
     │                     │    COT-00000001      │
     │                     │                      │
     │                     │ 8. INSERT cotizacion │
     │                     ├─────────────────────>│
     │                     │                      │
     │                     │ 9. INSERT detalles   │
     │                     ├─────────────────────>│
     │                     │                      │
     │                     │ 10. Calcular totales │
     │                     │     (subtotal, IGV)  │
     │                     │                      │
     │                     │ 11. UPDATE totales   │
     │                     ├─────────────────────>│
     │                     │                      │
     │                     │ 12. OK               │
     │                     │<─────────────────────┤
     │ 13. Cotización      │                      │
     │     creada          │                      │
     │<────────────────────┤                      │
     │                     │                      │
     │ 14. GET /api/       │                      │
     │     cotizaciones/   │                      │
     │     {id}/export_pdf/│                      │
     ├────────────────────>│                      │
     │                     │ 15. Generar PDF      │
     │                     │     con ReportLab    │
     │                     │     Incluir logo     │
     │                     │                      │
     │ 16. PDF (blob)      │                      │
     │<────────────────────┤                      │
     │                     │                      │
```

---

## 4. FLUJO DE ENTRENAMIENTO ML

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │     │  Backend │     │    BD    │     │   FS     │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                 │                │
     │ 1. Click       │                 │                │
     │ "Entrenar"     │                 │                │
     ├───────────────>│                 │                │
     │                │ 2. Extraer datos│                │
     │                │    de ventas    │                │
     │                ├────────────────>│                │
     │                │                 │                │
     │                │ 3. Ventas       │                │
     │                │<────────────────┤                │
     │                │                 │                │
     │                │ 4. Preparar     │                │
     │                │    features     │                │
     │                │    (RFM, etc)   │                │
     │                │                 │                │
     │                │ 5. Entrenar     │                │
     │                │    RFM Model    │                │
     │                │    (K-Means)    │                │
     │                │                 │                │
     │                │ 6. Entrenar     │                │
     │                │    Churn Model  │                │
     │                │    (RF)         │                │
     │                │                 │                │
     │                │ 7. Entrenar     │                │
     │                │    Recommender  │                │
     │                │    (Apriori)    │                │
     │                │                 │                │
     │                │ 8. Serializar   │                │
     │                │    modelos      │                │
     │                ├────────────────────────────────>│
     │                │                 │                │
     │                │ 9. Guardar      │                │
     │                │    metadata     │                │
     │                ├────────────────>│                │
     │                │                 │                │
     │                │ 10. OK          │                │
     │                │<────────────────┤                │
     │ 11. Modelos    │                 │                │
     │     entrenados │                 │                │
     │<───────────────┤                 │                │
     │                │                 │                │
```

---

## 5. ESTRUCTURA DE DIRECTORIOS DETALLADA

```
ERP_system/
├── backend/
│   ├── apps/
│   │   ├── authentication/
│   │   │   ├── models.py          # CustomUser
│   │   │   ├── serializers.py     # UserSerializer
│   │   │   ├── views.py           # Login, Register
│   │   │   ├── backends.py        # EmailBackend
│   │   │   └── middleware.py      # EmpresaMiddleware
│   │   │
│   │   ├── empresas/
│   │   │   ├── models.py          # Empresa
│   │   │   ├── serializers.py     # EmpresaSerializer
│   │   │   ├── views.py           # EmpresaViewSet
│   │   │   └── urls.py
│   │   │
│   │   ├── ventas/
│   │   │   ├── models.py          # Cliente, Venta, DetalleVenta
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── signals.py         # Post-save para inventario
│   │   │   └── urls.py
│   │   │
│   │   ├── compras/
│   │   │   ├── models.py          # Proveedor, OrdenCompra
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   │
│   │   ├── inventario/
│   │   │   ├── models/
│   │   │   │   ├── categoria.py
│   │   │   │   ├── producto.py
│   │   │   │   ├── movimiento.py
│   │   │   │   └── kardex.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── signals.py
│   │   │   └── urls.py
│   │   │
│   │   ├── cotizaciones/
│   │   │   ├── models.py          # Cotizacion, DetalleCotizacion
│   │   │   ├── serializers.py
│   │   │   ├── views.py           # CotizacionViewSet
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── utils/
│   │   │       └── pdf_generator.py  # CotizacionPDFGenerator
│   │   │
│   │   ├── ml_models/
│   │   │   ├── models.py          # MLModel
│   │   │   ├── views.py           # MLViewSet
│   │   │   ├── urls.py
│   │   │   ├── services/
│   │   │   │   ├── data_extractor.py
│   │   │   │   ├── training_service.py
│   │   │   │   └── prediction_service.py
│   │   │   ├── customer_segmentation/
│   │   │   │   └── rfm_segmentation.py
│   │   │   ├── churn_prediction/
│   │   │   │   └── churn_prediction.py
│   │   │   ├── product_recommendations/
│   │   │   │   └── association_rules.py
│   │   │   └── utils/
│   │   │       └── data_preparation.py
│   │   │
│   │   ├── ai_assistant/
│   │   │   ├── models.py          # Thread, Message
│   │   │   ├── views.py
│   │   │   ├── services/
│   │   │   │   └── openai_service.py
│   │   │   └── tools/
│   │   │       ├── ventas_tool.py
│   │   │       └── inventario_tool.py
│   │   │
│   │   └── core/
│   │       ├── permissions.py     # HasEmpresaPermission
│   │       └── models.py
│   │
│   ├── config/
│   │   ├── settings.py            # Configuración Django
│   │   ├── urls.py                # URLs principales
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── media/                     # Archivos subidos
│   │   ├── logos/                 # Logos de empresas
│   │   ├── comprobantes/          # PDFs de ventas
│   │   └── ml_models/             # Modelos ML serializados
│   │       └── {empresa_id}/
│   │           ├── rfm/
│   │           ├── churn/
│   │           └── recommendations/
│   │
│   ├── requirements.txt
│   ├── requirements_ml.txt
│   ├── manage.py
│   ├── Dockerfile
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   └── Layout.jsx
│   │   │   ├── Ventas/
│   │   │   │   ├── VentasList.jsx
│   │   │   │   └── VentasForm.jsx
│   │   │   ├── Cotizaciones/
│   │   │   │   ├── CotizacionList.jsx
│   │   │   │   └── CotizacionFormSimple.jsx
│   │   │   ├── ML/
│   │   │   │   ├── MLDashboard.jsx
│   │   │   │   ├── CustomerSegmentation.jsx
│   │   │   │   ├── ChurnPrediction.jsx
│   │   │   │   └── ProductRecommendations.jsx
│   │   │   └── Auth/
│   │   │       └── Login.jsx
│   │   │
│   │   ├── services/
│   │   │   ├── api.jsx            # Axios config
│   │   │   ├── ventasService.js
│   │   │   ├── cotizacionesService.js
│   │   │   └── mlService.js
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   │
│   │   ├── hooks/
│   │   │   └── useAuth.js
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.mjs
│   ├── Dockerfile
│   └── .env
│
├── datasets/                      # Datasets para ML
│   ├── ventas/
│   │   └── retail_sales_dataset.csv
│   └── productos/
│       └── Groceries_dataset.csv
│
├── docker-compose.yml
├── nginx.conf
├── .gitignore
├── README.md
├── DOCUMENTACION_COMPLETA_SISTEMA.md
└── ARQUITECTURA_TECNICA.md (este archivo)
```

---

## 6. MODELOS DE BASE DE DATOS (ERD)

```sql
-- EMPRESAS
CREATE TABLE empresas_empresa (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    ruc VARCHAR(11) UNIQUE NOT NULL,
    direccion VARCHAR(200),
    telefono VARCHAR(9),
    email VARCHAR(254),
    logo VARCHAR(100),  -- ImageField
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- USUARIOS
CREATE TABLE authentication_customuser (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP DEFAULT NOW()
);

-- CLIENTES
CREATE TABLE ventas_cliente (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    tipo_documento VARCHAR(20) NOT NULL,
    documento VARCHAR(20) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    direccion TEXT,
    telefono VARCHAR(20),
    email VARCHAR(254),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(empresa_id, documento)
);

-- PRODUCTOS
CREATE TABLE inventario_producto (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    categoria_id INTEGER REFERENCES inventario_categoria(id),
    sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    precio_compra DECIMAL(12, 2) DEFAULT 0.00,
    precio_venta DECIMAL(12, 2) DEFAULT 0.00,
    stock_actual DECIMAL(12, 2) DEFAULT 0.00,
    stock_minimo DECIMAL(12, 2) DEFAULT 0.00,
    unidad_medida VARCHAR(20) DEFAULT 'UND',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- VENTAS
CREATE TABLE ventas_venta (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    cliente_id INTEGER REFERENCES ventas_cliente(id),
    usuario_id INTEGER REFERENCES authentication_customuser(id),
    numero_venta VARCHAR(50) UNIQUE NOT NULL,
    fecha_emision DATE NOT NULL,
    tipo_comprobante VARCHAR(20) NOT NULL,
    serie VARCHAR(10),
    correlativo VARCHAR(20),
    moneda VARCHAR(3) DEFAULT 'PEN',
    subtotal DECIMAL(12, 2) DEFAULT 0.00,
    igv DECIMAL(12, 2) DEFAULT 0.00,
    total DECIMAL(12, 2) DEFAULT 0.00,
    estado VARCHAR(20) DEFAULT 'pendiente',
    metodo_pago VARCHAR(50),
    comprobante_pdf VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- DETALLE VENTAS
CREATE TABLE ventas_detalleventa (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER REFERENCES ventas_venta(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES inventario_producto(id),
    cantidad DECIMAL(12, 2) NOT NULL,
    precio_unitario DECIMAL(12, 2) NOT NULL,
    descuento DECIMAL(12, 2) DEFAULT 0.00,
    subtotal DECIMAL(12, 2) NOT NULL
);

-- COTIZACIONES
CREATE TABLE cotizaciones_cotizacion (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    cliente_id INTEGER REFERENCES ventas_cliente(id),
    usuario_creador_id INTEGER REFERENCES authentication_customuser(id),
    numero VARCHAR(50) UNIQUE NOT NULL,
    asunto VARCHAR(200),
    descripcion TEXT,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    fecha_aceptacion DATE,
    estado VARCHAR(20) DEFAULT 'borrador',
    moneda VARCHAR(3) DEFAULT 'PEN',
    subtotal DECIMAL(12, 2) DEFAULT 0.00,
    descuento DECIMAL(12, 2) DEFAULT 0.00,
    igv DECIMAL(12, 2) DEFAULT 0.00,
    total DECIMAL(12, 2) DEFAULT 0.00,
    incluye_igv BOOLEAN DEFAULT TRUE,
    porcentaje_igv DECIMAL(5, 2) DEFAULT 18.00,
    forma_pago VARCHAR(100) DEFAULT 'Contado',
    pago_facturas VARCHAR(200),
    tiempo_entrega VARCHAR(100),
    lugar_entrega TEXT,
    validez_oferta VARCHAR(100) DEFAULT '30 días',
    notas TEXT,
    terminos_condiciones TEXT,
    venta_id INTEGER REFERENCES ventas_venta(id),
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_modificacion TIMESTAMP DEFAULT NOW()
);

-- DETALLE COTIZACIONES
CREATE TABLE cotizaciones_detallecotizacion (
    id SERIAL PRIMARY KEY,
    cotizacion_id INTEGER REFERENCES cotizaciones_cotizacion(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES inventario_producto(id),
    codigo VARCHAR(50),
    descripcion TEXT NOT NULL,
    cantidad DECIMAL(12, 2) NOT NULL,
    precio_unitario DECIMAL(12, 2) NOT NULL,
    descuento_item DECIMAL(12, 2) DEFAULT 0.00,
    subtotal DECIMAL(12, 2) NOT NULL
);

-- MODELOS ML
CREATE TABLE ml_models_mlmodel (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas_empresa(id),
    model_type VARCHAR(50) NOT NULL,
    model_file VARCHAR(100) NOT NULL,
    metrics JSONB,
    trained_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(empresa_id, model_type)
);

-- ÍNDICES
CREATE INDEX idx_venta_empresa ON ventas_venta(empresa_id);
CREATE INDEX idx_venta_fecha ON ventas_venta(fecha_emision);
CREATE INDEX idx_venta_cliente ON ventas_venta(cliente_id);
CREATE INDEX idx_producto_empresa ON inventario_producto(empresa_id);
CREATE INDEX idx_producto_sku ON inventario_producto(sku);
CREATE INDEX idx_cotizacion_empresa ON cotizaciones_cotizacion(empresa_id);
CREATE INDEX idx_cotizacion_estado ON cotizaciones_cotizacion(estado);
CREATE INDEX idx_cotizacion_fecha ON cotizaciones_cotizacion(fecha_emision);
```

---

## 7. CONFIGURACIÓN DE SEGURIDAD

### settings.py (Producción)

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# SECURITY
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# CORS
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True

# HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

---

## 8. EJEMPLOS DE CÓDIGO

### 8.1 Serializer con Validación Multi-tenant

```python
# apps/ventas/serializers.py
from rest_framework import serializers
from .models import Venta, DetalleVenta
from apps.inventario.models import Producto

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 
                  'precio_unitario', 'descuento', 'subtotal']
        read_only_fields = ['subtotal']
    
    def validate_producto(self, value):
        """Validar que el producto pertenece a la empresa del usuario"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'empresa'):
            if value.empresa != request.user.empresa:
                raise serializers.ValidationError(
                    "El producto no pertenece a tu empresa"
                )
        return value
    
    def validate_cantidad(self, value):
        """Validar que hay stock suficiente"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        
        producto_id = self.initial_data.get('producto')
        if producto_id:
            producto = Producto.objects.get(id=producto_id)
            if producto.stock_actual < value:
                raise serializers.ValidationError(
                    f"Stock insuficiente. Disponible: {producto.stock_actual}"
                )
        return value

class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    
    class Meta:
        model = Venta
        fields = '__all__'
        read_only_fields = ['empresa', 'usuario', 'numero_venta', 
                            'subtotal', 'igv', 'total']
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        
        # Crear venta
        venta = Venta.objects.create(**validated_data)
        
        # Crear detalles y calcular totales
        subtotal = 0
        for detalle_data in detalles_data:
            detalle = DetalleVenta.objects.create(venta=venta, **detalle_data)
            subtotal += detalle.subtotal
        
        # Actualizar totales
        venta.subtotal = subtotal
        venta.igv = subtotal * 0.18
        venta.total = subtotal + venta.igv
        venta.save()
        
        return venta
```

### 8.2 ViewSet con Permisos Multi-tenant

```python
# apps/ventas/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.permissions import HasEmpresaPermission
from .models import Venta
from .serializers import VentaSerializer

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    permission_classes = [HasEmpresaPermission]
    filterset_fields = ['estado', 'cliente__id', 'fecha_emision']
    search_fields = ['numero_venta', 'cliente__nombre']
    ordering_fields = ['fecha_emision', 'total']
    ordering = ['-fecha_emision']
    
    def get_queryset(self):
        """Filtrar ventas por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def perform_create(self, serializer):
        """Asignar empresa y usuario automáticamente"""
        serializer.save(
            empresa=self.request.user.empresa,
            usuario=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Anular una venta"""
        venta = self.get_object()
        
        if venta.estado == 'anulado':
            return Response(
                {'error': 'La venta ya está anulada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        venta.estado = 'anulado'
        venta.save()
        
        # Devolver stock
        for detalle in venta.detalles.all():
            detalle.producto.stock_actual += detalle.cantidad
            detalle.producto.save()
        
        return Response({'message': 'Venta anulada correctamente'})
```

### 8.3 Servicio de ML

```python
# apps/ml_models/services/training_service.py
import os
import joblib
from django.conf import settings
from ..models import MLModel
from .data_extractor import DataExtractor
from ..customer_segmentation.rfm_segmentation import RFMSegmentation
from ..churn_prediction.churn_prediction import ChurnPredictor
from ..product_recommendations.association_rules import ProductRecommender

class MLTrainingService:
    def __init__(self, empresa):
        self.empresa = empresa
        self.data_extractor = DataExtractor(empresa)
    
    def train_all_models(self):
        """Entrenar todos los modelos para la empresa"""
        results = {
            'rfm': self.train_rfm(),
            'churn': self.train_churn(),
            'recommendations': self.train_recommendations()
        }
        return results
    
    def train_rfm(self):
        """Entrenar modelo de segmentación RFM"""
        try:
            # Extraer datos
            df = self.data_extractor.get_customer_purchase_data()
            
            if len(df) < 2:
                return {
                    'success': False,
                    'error': 'Se necesitan al menos 2 clientes con ventas'
                }
            
            # Entrenar modelo
            model_path = self._get_model_path('rfm')
            rfm_model = RFMSegmentation(model_path=model_path)
            rfm_model.fit(df)
            
            # Guardar modelo
            rfm_model.save_model()
            
            # Guardar metadata en BD
            MLModel.objects.update_or_create(
                empresa=self.empresa,
                model_type='rfm',
                defaults={
                    'model_file': model_path,
                    'metrics': {
                        'n_customers': len(df),
                        'n_clusters': 4
                    },
                    'is_active': True
                }
            )
            
            return {
                'success': True,
                'message': 'Modelo RFM entrenado correctamente'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_model_path(self, model_type):
        """Obtener ruta para guardar modelo"""
        model_dir = os.path.join(
            settings.MEDIA_ROOT,
            'ml_models',
            str(self.empresa.id),
            model_type
        )
        os.makedirs(model_dir, exist_ok=True)
        return os.path.join(model_dir, f'{model_type}_model.pkl')
```

---

## 9. TESTING

### 9.1 Tests Unitarios (Ejemplo)

```python
# apps/ventas/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta
from decimal import Decimal

User = get_user_model()

class VentaModelTest(TestCase):
    def setUp(self):
        # Crear empresa
        self.empresa = Empresa.objects.create(
            nombre='Test SA',
            ruc='12345678901'
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            empresa=self.empresa,
            tipo_documento='DNI',
            documento='12345678',
            nombre='Cliente Test'
        )
    
    def test_venta_creation(self):
        """Test crear venta"""
        venta = Venta.objects.create(
            empresa=self.empresa,
            cliente=self.cliente,
            usuario=self.user,
            numero_venta='V-0001',
            fecha_emision='2025-01-01',
            tipo_comprobante='Factura',
            subtotal=Decimal('100.00'),
            igv=Decimal('18.00'),
            total=Decimal('118.00')
        )
        
        self.assertEqual(venta.numero_venta, 'V-0001')
        self.assertEqual(venta.total, Decimal('118.00'))
        self.assertEqual(venta.estado, 'pendiente')
    
    def test_venta_multi_tenant(self):
        """Test que las ventas están aisladas por empresa"""
        # Crear otra empresa
        otra_empresa = Empresa.objects.create(
            nombre='Otra SA',
            ruc='98765432109'
        )
        
        # Crear venta para empresa 1
        venta1 = Venta.objects.create(
            empresa=self.empresa,
            cliente=self.cliente,
            usuario=self.user,
            numero_venta='V-0001',
            fecha_emision='2025-01-01'
        )
        
        # Verificar que solo hay 1 venta para empresa 1
        ventas_empresa1 = Venta.objects.filter(empresa=self.empresa)
        self.assertEqual(ventas_empresa1.count(), 1)
        
        # Verificar que no hay ventas para empresa 2
        ventas_empresa2 = Venta.objects.filter(empresa=otra_empresa)
        self.assertEqual(ventas_empresa2.count(), 0)
```

---

## 10. MONITOREO Y LOGS

### 10.1 Configuración de Logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

---

**FIN DEL DOCUMENTO TÉCNICO**


