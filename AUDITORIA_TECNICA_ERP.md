# AUDITORÍA TÉCNICA COMPLETA — ERP System
## Documento de Referencia para Revisión y Optimización

**Fecha de generación:** 2026-03-15
**Versión del sistema:** 1.0.0
**Entorno actual:** Desarrollo local + Supabase (PostgreSQL remoto)

---

## 1. STACK TECNOLÓGICO

### 1.1 Runtime & Lenguajes

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Backend Runtime | Python | 3.12.2 |
| Frontend Runtime | Node.js | 20.19.5 |
| Package Manager (Python) | pip | — |
| Package Manager (JS) | npm | 10.8.2 |
| Base de Datos | PostgreSQL | 15 (Docker) / Supabase |
| Servidor Web (Prod) | Gunicorn | — |
| Servidor Web (Frontend Prod) | Nginx | 1.25-alpine |
| Contenedores | Docker Compose | 3.9 |

### 1.2 Frameworks Principales

| Componente | Framework | Versión |
|------------|----------|---------|
| Backend API | Django | 4.2.7 |
| REST API | Django REST Framework | 3.14.0 |
| Frontend UI | React | 18.2.0 |
| Build Tool | Vite | 5.0.0 |
| UI Library Principal | Chakra UI | 2.10.6 |
| State Management (Server) | TanStack React Query | 5.74.4 |
| Routing | React Router DOM | 6.29.0 |
| HTTP Client | Axios | 1.7.9 |

---

## 2. DEPENDENCIAS BACKEND (Python)

### 2.1 Core Django

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| Django | 4.2.7 | Framework web principal |
| djangorestframework | 3.14.0 | API REST |
| djangorestframework-simplejwt | 5.3.0 | Autenticación JWT |
| django-cors-headers | 4.3.0 | CORS para frontend SPA |
| django-filter | 23.3 | Filtros en queryset |
| drf-nested-routers | 0.94.1 | Routers anidados (pagos de venta/compra) |
| whitenoise | 6.6.0 | Archivos estáticos en producción |
| asgiref | 3.7.2 | ASGI utilities |
| sqlparse | 0.4.4 | SQL parsing (Django internals) |

### 2.2 Base de Datos

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| psycopg2-binary | 2.9.9 | Driver PostgreSQL |

### 2.3 Procesamiento de Datos

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| pandas | 2.1.4 | Manipulación de datos |
| openpyxl | 3.1.2 | Lectura/escritura Excel |
| numpy | 1.26.4 | Cómputo numérico |

### 2.4 Machine Learning

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| scikit-learn | 1.3.2 | Algoritmos ML |
| prophet | 1.1.5 | Forecasting de series temporales |
| mlxtend | 0.23.0 | Market Basket Analysis |
| joblib | 1.3.2 | Persistencia de modelos |
| matplotlib | 3.8.2 | Visualización |
| seaborn | 0.13.0 | Visualización estadística |
| tqdm | 4.67.1 | Barras de progreso |

### 2.5 Integraciones Externas

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| openai | >=1.0.0 | API GPT-4 (AI Assistant) |
| requests | 2.31.0 | HTTP requests (APIs.net.pe DNI/RUC) |

### 2.6 Utilidades

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| Pillow | 10.1.0 / 10.4.0 | Manejo de imágenes (logos) |
| python-dotenv | 1.0.0 | Variables de entorno |
| python-jose | 3.3.0 | JWT encoding (legacy) |
| reportlab | 4.0.7 | Generación de PDFs |
| python-dateutil | 2.9.0 | Parsing de fechas |
| pytz | 2025.2 | Zonas horarias |

### 2.7 Problemas Detectados en Dependencias Backend

| # | Problema | Severidad | Recomendación |
|---|---------|-----------|---------------|
| 1 | **Pillow duplicado** (10.1.0 y 10.4.0 en requirements.txt) | Media | Eliminar la versión 10.1.0, mantener 10.4.0 |
| 2 | **pandas duplicado** (aparece dos veces) | Baja | Eliminar la segunda aparición |
| 3 | **python-jose** sin uso claro (JWT ya se maneja con simplejwt) | Baja | Evaluar si se usa; si no, eliminar |
| 4 | **openai>=1.0.0** sin version pin | Media | Fijar versión específica para reproducibilidad |
| 5 | **django-redis** no está en requirements.txt pero se referencia en settings.py | Media | Agregar si se planea usar Redis |
| 6 | **Django 4.2.7** tiene versiones más recientes (4.2.x LTS) | Baja | Actualizar a 4.2.17+ (último LTS patch) |
| 7 | **ML dependencies mezcladas** con core en un solo requirements.txt | Baja | Separar en requirements_ml.txt (ya existe el archivo pero no se usa independientemente) |

---

## 3. DEPENDENCIAS FRONTEND (Node.js)

### 3.1 Dependencies

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| @chakra-ui/react | ^2.10.6 | UI Library principal |
| @chakra-ui/icons | ^2.2.4 | Iconos Chakra |
| @emotion/react | ^11.14.0 | CSS-in-JS (requerido por Chakra) |
| @emotion/styled | ^11.14.0 | Styled components (requerido por Chakra) |
| @mui/material | ^7.1.0 | Material UI |
| @mui/icons-material | ^7.1.0 | Iconos MUI |
| @reduxjs/toolkit | ^2.5.0 | Redux (state management) |
| @tanstack/react-query | ^5.74.4 | Server state management |
| axios | ^1.7.9 | HTTP client |
| bootstrap | ^5.3.5 | CSS framework |
| chart.js | ^4.4.7 | Gráficos |
| date-fns | ^3.3.0 | Manejo de fechas |
| framer-motion | ^10.18.0 | Animaciones (requerido por Chakra) |
| lucide-react | ^0.476.0 | Iconos |
| openai | ^4.95.1 | API OpenAI en frontend |
| path | ^0.12.7 | Path utilities |
| react | ^18.2.0 | UI library |
| react-bootstrap | ^2.10.9 | Bootstrap components |
| react-chartjs-2 | ^5.3.0 | Wrapper Chart.js para React |
| react-dom | ^18.2.0 | React DOM renderer |
| react-hook-form | ^7.54.2 | Formularios |
| react-icons | ^5.5.0 | Iconos |
| react-redux | ^9.2.0 | Redux bindings para React |
| react-router-dom | ^6.29.0 | Routing |
| react-toastify | ^9.1.3 | Notificaciones toast |
| recharts | ^3.3.0 | Gráficos (alternativa a chart.js) |
| xlsx | ^0.18.5 | Lectura/escritura Excel |
| zod | ^3.22.4 | Validación de esquemas |

### 3.2 DevDependencies

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| @vitejs/plugin-react | ^4.3.4 | Plugin Vite para React |
| vite | ^5.0.0 | Build tool |
| eslint | ^8.57.0 | Linter |
| eslint-config-react-app | ^7.0.0 | Config ESLint |
| tailwindcss | ^4.0.9 | CSS utility-first |
| postcss | ^8.5.3 | CSS processing |
| autoprefixer | ^10.4.20 | CSS autoprefixer |
| @testing-library/jest-dom | ^6.6.3 | Test matchers |
| @testing-library/react | ^14.2.0 | React testing |
| @testing-library/user-event | ^14.6.1 | User event simulation |
| jest | ^29.7.0 | Test runner |

### 3.3 Problemas Detectados en Dependencias Frontend

| # | Problema | Severidad | Recomendación |
|---|---------|-----------|---------------|
| 1 | **3 UI Libraries simultáneas**: Chakra UI + MUI + Bootstrap + Tailwind | Alta | Estandarizar en UNA sola (Chakra UI recomendado) |
| 2 | **3 librerías de iconos**: @chakra-ui/icons + @mui/icons-material + react-icons + lucide-react | Alta | Estandarizar en react-icons (más completa) |
| 3 | **2 librerías de gráficos**: chart.js/react-chartjs-2 + recharts | Media | Elegir una sola |
| 4 | **Redux sin uso aparente**: @reduxjs/toolkit + react-redux instalados pero React Query maneja el state | Media | Eliminar si no se usa |
| 5 | **openai en frontend**: API key de OpenAI expuesta en cliente | **Crítica** | Mover llamadas a OpenAI al backend |
| 6 | **path** en dependencies: paquete Node.js que no se necesita en frontend | Baja | Eliminar |
| 7 | **Tailwind CSS v4** instalado pero no se configura como sistema principal | Baja | Decidir si usar o eliminar |
| 8 | **2 instancias de API**: `src/api.jsx` y `src/services/api.jsx` con configuraciones diferentes | Alta | Unificar en una sola instancia |
| 9 | **react-hook-form + zod** instalados pero sin uso sistemático | Baja | Implementar validación consistente o eliminar |
| 10 | **Bundle size excesivo** por dependencias redundantes | Alta | Audit con `npm run build -- --report` |

---

## 4. ESTRUCTURA DE CARPETAS

```
ERP_system/
├── .gitignore
├── docker-compose.yml
├── package.json                          # Root (no se usa para build)
├── ENV_EXAMPLE.txt
├── LEEME_SEGURIDAD.txt
├── check_security.py
├── generate_secrets.py
│
├── backend/
│   ├── Dockerfile                        # Python 3.11-slim + Gunicorn
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements_ml.txt
│   ├── start_server.sh
│   ├── .env                              # Variables de entorno (NO en git)
│   ├── .env.example
│   │
│   ├── config/
│   │   ├── settings.py                   # Configuración principal Django
│   │   ├── urls.py                       # URLs raíz
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   ├── models.py                     # ⚠️ Modelo legacy (Compra)
│   │   ├── serializers.py                # ⚠️ Serializer legacy
│   │   └── views.py                      # ⚠️ Vista legacy
│   │
│   ├── apps/
│   │   ├── authentication/               # Login, JWT, CustomUser
│   │   │   ├── models.py                 # CustomUser (AbstractUser)
│   │   │   ├── views.py                  # LoginView, UserProfileView
│   │   │   ├── serializers.py
│   │   │   ├── backends.py               # EmailBackend
│   │   │   ├── urls.py
│   │   │   └── migrations/               # 1 migración
│   │   │
│   │   ├── empresas/                     # Gestión de empresas/tenants
│   │   │   ├── models.py                 # Empresa (con uuid field)
│   │   │   ├── views.py                  # EmpresaViewSet
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   └── migrations/               # 3 migraciones
│   │   │
│   │   ├── ventas/                       # Ventas, clientes, facturas, pagos
│   │   │   ├── models.py                 # 7 modelos
│   │   │   ├── views.py                  # 6 ViewSets + 1 APIView
│   │   │   ├── serializers.py            # 7 serializers
│   │   │   ├── urls.py
│   │   │   ├── signals.py
│   │   │   └── migrations/               # 16 migraciones
│   │   │
│   │   ├── compras/                      # Compras, proveedores, OC, pagos
│   │   │   ├── models.py                 # 8 modelos
│   │   │   ├── views.py                  # 6 ViewSets
│   │   │   ├── serializers.py            # 10 serializers
│   │   │   ├── urls.py
│   │   │   ├── signals.py
│   │   │   ├── utils/
│   │   │   └── migrations/               # 8 migraciones
│   │   │
│   │   ├── inventario/                   # Productos, stock, kardex, MP, PT
│   │   │   ├── models/                   # 9 modelos (en archivos separados)
│   │   │   │   ├── producto.py
│   │   │   │   ├── almacen.py
│   │   │   │   ├── categoria.py
│   │   │   │   ├── stock.py
│   │   │   │   ├── movimiento_inventario.py
│   │   │   │   ├── ajuste_inventario.py
│   │   │   │   ├── inventario_materias_primas.py
│   │   │   │   └── inventario_productos_terminados.py
│   │   │   ├── views.py                  # 12 ViewSets/Views
│   │   │   ├── serializers.py            # 19 serializers
│   │   │   ├── urls.py
│   │   │   ├── signals.py
│   │   │   ├── utils/
│   │   │   ├── management/commands/      # 2 comandos custom
│   │   │   └── migrations/               # 9 migraciones
│   │   │
│   │   ├── produccion/                   # Recetas, órdenes de producción
│   │   │   ├── models.py                 # 8 modelos
│   │   │   ├── views.py                  # 3 ViewSets/Views
│   │   │   ├── serializers.py            # 11 serializers
│   │   │   ├── urls.py
│   │   │   ├── signals.py
│   │   │   ├── services/
│   │   │   └── migrations/               # 2 migraciones
│   │   │
│   │   ├── cotizaciones/                 # Cotizaciones y detalles
│   │   │   ├── models.py                 # 2 modelos
│   │   │   ├── views.py                  # CotizacionViewSet
│   │   │   ├── serializers.py            # 4 serializers
│   │   │   ├── urls.py
│   │   │   ├── utils/                    # PDF export
│   │   │   └── migrations/               # 2 migraciones
│   │   │
│   │   ├── dashboard/                    # Dashboard y reportes
│   │   │   ├── views.py                  # 9 APIViews
│   │   │   ├── urls.py
│   │   │   ├── templates/
│   │   │   └── migrations/               # 0 migraciones (solo vistas)
│   │   │
│   │   ├── core/                         # Perfiles, permisos, middleware
│   │   │   ├── models/                   # Base models (TenantModel, etc.)
│   │   │   ├── models.py                 # Empresa, Usuario legacy
│   │   │   ├── views.py                  # Permisos, DNI/RUC, tipo cambio
│   │   │   ├── serializers.py
│   │   │   ├── permissions.py            # HasEmpresaPermission, ModulePermission
│   │   │   ├── signals.py
│   │   │   ├── middleware/
│   │   │   │   └── tenant.py             # TenantMiddleware (RLS)
│   │   │   ├── services/
│   │   │   └── migrations/               # 1 migración
│   │   │
│   │   ├── ai_assistant/                 # Asistente IA (OpenAI, Claude)
│   │   │   ├── models.py                 # 4 modelos
│   │   │   ├── views.py                  # 14 Views/ViewSets
│   │   │   ├── serializers.py            # 4 serializers
│   │   │   ├── urls.py
│   │   │   ├── services/
│   │   │   ├── tools/
│   │   │   └── migrations/               # 4 migraciones
│   │   │
│   │   └── ml_models/                    # Machine Learning
│   │       ├── models.py                 # 3 modelos
│   │       ├── views.py                  # MLModelViewSet
│   │       ├── urls.py
│   │       ├── services/
│   │       ├── utils/
│   │       ├── customer_analytics/
│   │       ├── demand_forecasting/
│   │       ├── product_recommendations/
│   │       └── migrations/               # 2 migraciones
│   │
│   └── media/                            # Archivos subidos
│       ├── comprobantes/
│       ├── logos/
│       └── ventas/
│
├── frontend/
│   ├── Dockerfile                        # Node 18 → Nginx 1.25
│   ├── nginx.conf                        # CSP headers, SPA fallback
│   ├── package.json
│   ├── vite.config.mjs
│   ├── index.html
│   │
│   └── src/
│       ├── App.jsx                       # Router principal (52 rutas)
│       ├── api.jsx                       # Instancia Axios #1 (auth)
│       ├── main.jsx                      # Entry point
│       │
│       ├── components/
│       │   ├── Auth/                     # Login (1 componente)
│       │   ├── Dashboard/                # 5 componentes
│       │   ├── Ventas/                   # 17 componentes
│       │   ├── Compras/                  # 13 componentes
│       │   ├── Inventario/               # 21 componentes
│       │   ├── Produccion/               # 10 componentes
│       │   ├── Cotizaciones/             # 4 componentes
│       │   ├── Proveedores/              # 4 componentes
│       │   ├── Cuentas/                  # 6 componentes
│       │   ├── ML/                       # 4 componentes
│       │   ├── AIAssistant/              # 6 componentes
│       │   ├── Layout/                   # 5 componentes
│       │   ├── Empresa/                  # 1 componente
│       │   ├── Empresas/                 # 1 componente
│       │   ├── Landing/                  # 1 componente
│       │   ├── Navbar/                   # 1 componente
│       │   ├── Reportes/                 # 5 componentes
│       │   ├── common/                   # 7 componentes reutilizables
│       │   ├── context/                  # AuthContext
│       │   ├── PrivateRoute.jsx
│       │   └── NotFound.jsx
│       │
│       ├── services/                     # 19 servicios
│       │   ├── api.jsx                   # Instancia Axios #2 (general)
│       │   ├── auth.service.js
│       │   ├── ventas.service.js
│       │   ├── compras.service.js
│       │   ├── inventario.service.js
│       │   ├── produccion.service.js
│       │   ├── cotizacionesService.js
│       │   ├── dashboard.service.js
│       │   ├── productos.service.js
│       │   ├── clientes.service.js
│       │   ├── proveedores.service.js
│       │   ├── almacenes.service.js
│       │   ├── categorias.service.js
│       │   ├── cuentas.service.js
│       │   ├── igv.service.js
│       │   ├── mlService.js
│       │   ├── ai.service.js
│       │   ├── ventas-assistant.service.js
│       │   └── compras-assistant.service.js
│       │
│       ├── pages/                        # 4 páginas
│       ├── utils/                        # 3 utilidades
│       ├── config/                       # axios.js, config.js
│       ├── hooks/
│       ├── router/                       # index.jsx, routes.js (legacy)
│       ├── styles/
│       └── types/
│
├── migrations_sql/                       # 8 scripts SQL ejecutados
│   ├── README.md
│   ├── 01_corregir_fk_tipos.sql
│   ├── 02_agregar_empresa_id.sql
│   ├── 03_poblar_empresa_id.sql
│   ├── 04_crear_indices.sql
│   ├── 05_activar_rls.sql
│   ├── 06_soft_delete.sql
│   ├── 07_crear_enums.sql
│   └── 08_auditoria.sql
│
├── scripts/                              # ML training scripts
│   ├── analyze_datasets.py
│   ├── train_models_standalone.py
│   └── train_with_real_data.py
│
├── datasets/                             # Datos para ML
│   ├── clientes/
│   ├── inventario/
│   ├── productos/
│   ├── raw/
│   └── ventas/
│
└── [23 archivos .md de documentación]
```

---

## 5. ARQUITECTURA DE BASE DE DATOS

### 5.1 Configuración

| Parámetro | Valor |
|-----------|-------|
| Motor | PostgreSQL 15 |
| Host actual | Supabase Session Pooler (`aws-0-us-west-2.pooler.supabase.com`) |
| SSL | `require` |
| Connection pooling | CONN_MAX_AGE=60, Supavisor (session mode) |
| Transacciones | ATOMIC_REQUESTS=True |
| Connect timeout | 30s |

### 5.2 Modelos de Datos (48 tablas)

| Módulo | Modelos | Tabla(s) |
|--------|---------|----------|
| **authentication** | CustomUser | `authentication_customuser` |
| **empresas** | Empresa | `empresas_empresa` |
| **ventas** | Cliente, Venta, DetalleVenta, Factura, OrdenVenta, PagoVenta, ComprobantePago | 7 tablas |
| **compras** | Proveedor, Compra, CompraDetalle, PagoCompra, ComprobantePago, OrdenCompra, OrdenCompraDetalle, RecepcionCompra, CompraRecurrente | 8 tablas |
| **inventario** | Producto, Almacen, Categoria, Stock, MovimientoInventario, AjusteInventario, InventarioMateriasPrimas, InventarioProductosTerminados | 8 tablas |
| **produccion** | RecetaProducto, RecetaDetalle, OrdenProduccion, ConsumoReal, ProductionOutput, ProductionWaste, ProductionCost, HistorialOrdenProduccion | 8 tablas |
| **cotizaciones** | Cotizacion, DetalleCotizacion | 2 tablas |
| **ai_assistant** | Conversation, Message, AIInsight, AIAction | 4 tablas |
| **ml_models** | MLModel, MLPrediction, TrainingJob | 3 tablas |
| **core** | Perfil, Usuario, Empresa (legacy) | 3 tablas |
| **audit** | audit_log | 1 tabla (creada via SQL) |

### 5.3 Multi-Tenancy

| Componente | Estado |
|------------|--------|
| Estrategia | Shared DB, shared schema |
| Columna de tenant | `empresa_id` (BIGINT) + `empresa_uuid` (UUID) |
| RLS activado | 55 tablas |
| Políticas RLS | 45 (duales: bigint + UUID) |
| Triggers auto_set_empresa_id | 20 tablas |
| Triggers auto_set_empresa_uuid | 41 tablas |
| Middleware Django | TenantMiddleware (sets session vars) |
| Soft Delete | 14 tablas (`deleted_at`, `deleted_by`) |
| Auditoría | `audit_log` + 33 triggers |
| Índices estratégicos | 56 en `empresa_id` + 44 en `empresa_uuid` |
| CHECK constraints (estados) | 16 |

### 5.4 Migración UUID — Estado

| Etapa | Descripción | Estado |
|-------|-------------|--------|
| 1 | Agregar UUID a `empresas_empresa` | ✅ Completada |
| 2 | Agregar `empresa_uuid` a 44 tablas | ✅ Completada |
| 3 | Poblar `empresa_uuid` via JOINs | ✅ Completada |
| 4 | Crear índices UUID | ✅ Completada |
| 5 | Validar integridad | ✅ Completada (0 errores) |
| 6 | NOT NULL + FKs UUID | ✅ Completada |
| 7 | Actualizar RLS/triggers/funciones | ✅ Completada |
| 8 | Actualizar Django middleware/models | ✅ Completada |
| 9 | Swap final (DROP bigint) | ⏳ Pendiente |
| 10 | Verificación post-swap | ⏳ Pendiente |

### 5.5 Migraciones Django por App

| App | Cantidad |
|-----|----------|
| ventas | 16 |
| inventario | 9 |
| compras | 8 |
| ai_assistant | 4 |
| empresas | 3 |
| cotizaciones | 2 |
| produccion | 2 |
| ml_models | 2 |
| authentication | 1 |
| core | 1 |
| dashboard | 0 |

---

## 6. SEGURIDAD

### 6.1 Autenticación

| Parámetro | Valor |
|-----------|-------|
| Modelo de usuario | CustomUser (AbstractUser) |
| Campo de login | email |
| Mecanismo | JWT (SimpleJWT) |
| Access Token Lifetime | 15 minutos |
| Refresh Token Lifetime | 7 días |
| Rotate Refresh Tokens | Sí |
| Blacklist After Rotation | Sí |
| Algoritmo | HS256 |
| Signing Key | Variable de entorno (`JWT_SIGNING_KEY`) |
| Authentication Backends | EmailBackend + ModelBackend |

### 6.2 Permisos

| Clase | Estado | Descripción |
|-------|--------|-------------|
| `HasEmpresaPermission` | Implementado | Verifica `obj.empresa == request.user.empresa` |
| `ModulePermission` | **Incompleto** | Siempre retorna `True` (stub) |
| `IsAuthenticated` | Default | Configurado globalmente en REST_FRAMEWORK |

### 6.3 Headers de Seguridad

| Header/Config | Valor | Entorno |
|---------------|-------|---------|
| SECURE_CONTENT_TYPE_NOSNIFF | True | Todos |
| X_FRAME_OPTIONS | DENY | Todos |
| SECURE_BROWSER_XSS_FILTER | True | Todos |
| SECURE_REFERRER_POLICY | strict-origin-when-cross-origin | Todos |
| SESSION_COOKIE_HTTPONLY | True | Todos |
| CSRF_COOKIE_HTTPONLY | True | Todos |
| SESSION_COOKIE_SECURE | True | Producción |
| CSRF_COOKIE_SECURE | True | Producción |
| SECURE_HSTS_SECONDS | 31536000 | Producción |
| SECURE_HSTS_PRELOAD | True | Producción |

### 6.4 CORS

| Config | Valor |
|--------|-------|
| Orígenes permitidos | Variable `CORS_ALLOWED_ORIGINS` |
| Allow Credentials | True |
| Validación en producción | Requiere orígenes explícitos |

---

## 7. API ENDPOINTS

### 7.1 Resumen por Módulo

| Módulo | Prefijo | Endpoints Principales |
|--------|---------|----------------------|
| Autenticación | `/api/token/`, `/api/auth/` | login, refresh, profile |
| Empresas | `/api/empresas/` | CRUD + upload logo |
| Ventas | `/api/ventas/` | clientes, ventas, facturas, pagos |
| Compras | `/api/compras/` | compras, proveedores, OC, recepciones, pagos |
| Inventario | `/api/inventario/` | productos, almacenes, stock, kardex, MP, PT, carga masiva |
| Producción | `/api/produccion/` | recetas, órdenes, dashboard |
| Cotizaciones | `/api/cotizaciones/` | CRUD + export PDF |
| Dashboard | `/api/dashboard/` | resumen, stats, utilidad, IGV, reportes |
| AI Assistant | `/api/ai/` | conversations, threads, analista comercial |
| ML | `/api/ml/` | modelos ML |
| Core | `/api/core/` | usuarios, perfiles, DNI/RUC, tipo cambio |

### 7.2 Rutas Frontend (52 rutas)

| Categoría | Rutas |
|-----------|-------|
| Públicas | `/` (Landing), `/login` |
| Dashboard | `/app/dashboard` |
| Ventas | 6 rutas (lista, nueva, detalle, editar, pagos) |
| Clientes | `/app/clientes` |
| Inventario | 8 rutas (lista, nuevo, editar, kardex, MP, PT, carga masiva) |
| Compras | 8 rutas (lista, nueva, OC, detalle, editar, pagos) |
| Proveedores | 3 rutas (lista, nuevo, editar) |
| Cotizaciones | 4 rutas (lista, nueva, detalle, editar) |
| Cuentas | 4 rutas (por cobrar, por pagar, registrar pagos) |
| Producción | 8 rutas (dashboard, recetas, órdenes) |
| Configuración | `/app/configuracion` |
| AI/ML | 2 rutas (ai-assistant, ml-dashboard) |
| Catch-all | `*` → NotFound |

---

## 8. INFRAESTRUCTURA Y DEVOPS

### 8.1 Docker

| Servicio | Imagen | Puerto |
|----------|--------|--------|
| db | postgres:15 | 5432 |
| backend | Python 3.11-slim + Gunicorn | 8080 |
| frontend | Node 18 → Nginx 1.25-alpine | 3000→80 |

### 8.2 CI/CD

| Componente | Estado |
|------------|--------|
| GitHub Actions | **No configurado** |
| Jenkins | **No configurado** |
| Automated Tests | **No configurado** |
| Linting Pipeline | **No configurado** |

### 8.3 Testing

| Tipo | Estado | Archivos |
|------|--------|----------|
| Backend (Django) | **No hay tests** | 0 archivos |
| Frontend (Jest) | **Mínimo** | `App.test.js`, `Login.test.js` |
| E2E | **No existe** | — |
| Coverage | **No configurado** | — |

### 8.4 Monitoring

| Componente | Estado |
|------------|--------|
| Error tracking (Sentry) | No configurado |
| APM | No configurado |
| Logs estructurados | Parcial (Django logging) |
| Health checks | No implementado |
| Métricas de DB | No configurado |

---

## 9. COMPONENTES FRONTEND — ESTADÍSTICAS

| Categoría | Cantidad |
|-----------|----------|
| Componentes JSX | ~115 |
| Servicios | 19 |
| Páginas | 4 |
| Contextos | 1 (AuthContext) |
| Hooks custom | 0 |
| Utilidades | 3 |
| Tests | 2 |
| Instancias de API | 2 (inconsistentes) |

---

## 10. HALLAZGOS CRÍTICOS Y RECOMENDACIONES

### 10.1 Seguridad (Crítica)

| # | Hallazgo | Riesgo | Acción |
|---|---------|--------|--------|
| 1 | **OpenAI API key en frontend** (`openai` en package.json) | Crítico | Mover todas las llamadas OpenAI al backend |
| 2 | **ModulePermission siempre retorna True** | Alto | Implementar lógica de permisos por módulo |
| 3 | **Credenciales en migrations_sql/README.md** | Medio | Limpiar credenciales del repositorio |
| 4 | **2 instancias de API con interceptores diferentes** | Alto | Unificar para evitar bypass de seguridad |
| 5 | **core/signals.py usa User en lugar de CustomUser** | Medio | Corregir referencia al modelo correcto |

### 10.2 Arquitectura (Alta)

| # | Hallazgo | Impacto | Acción |
|---|---------|---------|--------|
| 1 | **Modelos duplicados**: Empresa en core/ y empresas/, Almacen duplicado | Confusión | Eliminar modelos legacy en core/ y config/ |
| 2 | **3+ UI libraries** (Chakra + MUI + Bootstrap + Tailwind) | Bundle size, inconsistencia visual | Estandarizar en Chakra UI |
| 3 | **Sin CI/CD pipeline** | Riesgo de deploy | Implementar GitHub Actions básico |
| 4 | **Sin tests automatizados** | Riesgo de regresión | Implementar tests unitarios y de integración |
| 5 | **23 archivos .md en raíz** | Desorden | Consolidar en una carpeta `docs/` |
| 6 | **Archivos legacy en config/** (models.py, views.py, serializers.py) | Confusión | Eliminar si no se usan |

### 10.3 Performance (Media)

| # | Hallazgo | Impacto | Acción |
|---|---------|---------|--------|
| 1 | **Supabase us-west-2 desde Perú/LATAM** | Latencia ~1-2s por request | Evaluar región más cercana o CDN |
| 2 | **CONN_MAX_AGE=60** con pooler externo | Conexiones estancadas | Ajustar a 0 con session pooler |
| 3 | **No hay caché de queries** frecuentes | Queries repetitivas | Implementar Redis para producción |
| 4 | **ML dependencies en el mismo proceso** | Memoria excesiva | Separar ML en microservicio o worker |
| 5 | **Bundle frontend no optimizado** | Tiempo de carga | Code splitting, lazy loading de rutas |

### 10.4 Mantenibilidad (Media)

| # | Hallazgo | Impacto | Acción |
|---|---------|---------|--------|
| 1 | **Naming inconsistente** en servicios (camelCase vs kebab-case) | Confusión | Estandarizar naming convention |
| 2 | **No hay .env.example en frontend** | Onboarding difícil | Crear con VITE_API_URL documentado |
| 3 | **router/index.jsx y router/routes.js** sin uso real | Código muerto | Eliminar archivos sin uso |
| 4 | **debug_compras.js, test_kardex.js** en raíz | Desorden | Mover a carpeta `scripts/` o eliminar |
| 5 | **Pillow duplicado en requirements.txt** | Conflicto potencial | Limpiar duplicados |

---

## 11. RESUMEN CUANTITATIVO

| Métrica | Valor |
|---------|-------|
| **Total tablas en DB** | ~48 |
| **Total modelos Django** | ~42 |
| **Total serializers** | ~55 |
| **Total ViewSets/Views** | ~45 |
| **Total API endpoints** | ~100+ |
| **Total rutas frontend** | 52 |
| **Total componentes React** | ~115 |
| **Total servicios frontend** | 19 |
| **Total migraciones Django** | 48 |
| **Total migraciones SQL** | 8 |
| **Total dependencias backend** | 28 |
| **Total dependencias frontend** | 33 + 11 dev |
| **Total archivos .md** | 23 |
| **Tests automatizados** | 2 (frontend) |
| **CI/CD pipelines** | 0 |

---

## 12. PRIORIDADES DE OPTIMIZACIÓN

### Prioridad 1 — Inmediata (Seguridad)
1. Eliminar `openai` del frontend y mover al backend
2. Implementar `ModulePermission` con lógica real
3. Limpiar credenciales de la documentación
4. Unificar las 2 instancias de API en frontend

### Prioridad 2 — Corto Plazo (Estabilidad)
1. Implementar CI/CD básico (lint + test + build)
2. Agregar tests unitarios (backend: al menos modelos y views críticas)
3. Eliminar código legacy (config/models.py, modelos duplicados)
4. Estandarizar UI library (eliminar MUI y Bootstrap, quedar con Chakra)

### Prioridad 3 — Mediano Plazo (Performance)
1. Implementar Redis cache para producción
2. Code splitting y lazy loading en frontend
3. Evaluar región de Supabase vs latencia
4. Separar ML en worker/microservicio
5. Completar migración UUID (etapa 9)

### Prioridad 4 — Largo Plazo (Escalabilidad)
1. Implementar WebSockets para notificaciones real-time
2. Particionamiento de tablas grandes
3. Read replicas para reportes
4. E2E testing con Playwright
5. Monitoring completo (Sentry + métricas)

---

**Documento generado automáticamente — Auditoría Técnica ERP System**
**Para revisión por equipo técnico y stakeholders**
