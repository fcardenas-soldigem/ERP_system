# 📋 Módulo de Cotizaciones - Sistema ERP

## ✨ Características Implementadas

### Backend (Django REST Framework)

#### 1. **Modelos de Base de Datos**
- ✅ **Cotizacion**: Modelo principal con toda la información de la cotización
  - Número automático (COT-00000001, COT-00000002, etc.)
  - Estados: Borrador, Enviada, Aceptada, Rechazada, Vencida, Convertida
  - Soporte para múltiples monedas (PEN, USD)
  - Cálculo automático de totales (subtotal, descuento, IGV, total)
  - Fechas de emisión, vencimiento y aceptación
  - Condiciones comerciales (forma de pago, tiempo de entrega, lugar de entrega)
  - Notas y términos y condiciones
  - Relación con venta (si se convierte)

- ✅ **DetalleCotizacion**: Detalles de productos/servicios
  - Soporte para productos del inventario o servicios personalizados
  - Código, descripción, cantidad, precio unitario
  - Descuentos por ítem
  - Cálculo automático de subtotales
  - Orden de visualización

#### 2. **API REST Endpoints**
```
GET    /api/cotizaciones/                    - Listar cotizaciones
POST   /api/cotizaciones/                    - Crear cotización
GET    /api/cotizaciones/{id}/               - Ver detalle
PUT    /api/cotizaciones/{id}/               - Actualizar
DELETE /api/cotizaciones/{id}/               - Eliminar
POST   /api/cotizaciones/{id}/cambiar-estado/ - Cambiar estado
POST   /api/cotizaciones/{id}/duplicar/       - Duplicar cotización
POST   /api/cotizaciones/{id}/convertir-venta/ - Convertir a venta
GET    /api/cotizaciones/{id}/exportar-pdf/   - Exportar PDF
GET    /api/cotizaciones/estadisticas/        - Estadísticas
```

#### 3. **Generación de PDF Profesional**
- ✅ Diseño elegante y profesional con colores corporativos
- ✅ Logo de la empresa personalizable (se carga desde el modelo Empresa)
- ✅ Encabezado con información de la empresa
- ✅ Información del cliente y fechas
- ✅ Tabla de productos/servicios con formato profesional
- ✅ Tabla de totales destacada
- ✅ Condiciones comerciales
- ✅ Notas y términos y condiciones
- ✅ Sección de firma
- ✅ Pie de página con número de cotización y fecha de generación

#### 4. **Características Adicionales del Backend**
- ✅ Multi-tenancy (por empresa)
- ✅ Permisos y autenticación
- ✅ Filtros por estado, cliente y búsqueda
- ✅ Validaciones de datos
- ✅ Auditoría (fechas de creación y modificación)
- ✅ Cálculos automáticos de totales

### Frontend (React + Chakra UI)

#### 1. **Componentes Implementados**
- ✅ **CotizacionList**: Listado de cotizaciones con filtros y acciones
  - Búsqueda por número, asunto o cliente
  - Filtro por estado
  - Tabla responsive con información clave
  - Menú de acciones (ver, editar, PDF, duplicar, convertir, eliminar)
  - Badges de estado con colores

- ✅ **CotizacionForm**: Formulario completo para crear/editar
  - Selección de cliente
  - Asunto y descripción
  - Configuración (moneda, IGV, validez)
  - Tabla dinámica de productos/servicios
  - Autocompletado desde inventario
  - Cálculo automático de totales en tiempo real
  - Condiciones comerciales
  - Notas y términos
  - Validaciones del lado del cliente

#### 2. **Funcionalidades del Frontend**
- ✅ Crear nueva cotización
- ✅ Editar cotización existente
- ✅ Ver listado con filtros
- ✅ Exportar a PDF con un clic
- ✅ Duplicar cotización
- ✅ Convertir a venta
- ✅ Cambiar estado
- ✅ Eliminar cotización
- ✅ Cálculos automáticos de totales
- ✅ Interfaz intuitiva y profesional

#### 3. **Integración con el Sistema**
- ✅ Menú lateral con icono de cotizaciones
- ✅ Rutas configuradas en App.jsx
- ✅ Servicio API completo (cotizacionesService.js)
- ✅ Integración con módulos de Clientes e Inventario

## 🎨 Diseño del PDF

El PDF generado incluye:

### Características de Diseño
- **Colores Corporativos Elegantes**:
  - Azul oscuro (#2C3E50) para encabezados
  - Azul corporativo (#3498DB) para acentos
  - Verde (#27AE60) para totales
  - Gris claro (#ECF0F1) para fondos

- **Estructura Profesional**:
  1. Encabezado con logo y datos de la empresa
  2. Título "COTIZACIÓN" con número
  3. Información del cliente en tabla elegante
  4. Detalle de productos/servicios
  5. Tabla de totales destacada
  6. Condiciones comerciales
  7. Notas y términos
  8. Sección de firma
  9. Pie de página con número y fecha

### Logo Personalizable
- El logo se carga automáticamente desde el modelo `Empresa`
- Ubicación: Campo `logo` en el modelo Empresa
- Formato: Cualquier formato de imagen (PNG, JPG, etc.)
- Tamaño recomendado: 200x100 px (se ajusta automáticamente)

## 📦 Instalación y Configuración

### 1. Backend

#### Dependencias Instaladas
```bash
reportlab==4.4.4  # Para generación de PDFs
```

#### Migraciones Aplicadas
```bash
python manage.py makemigrations cotizaciones
python manage.py migrate cotizaciones
```

#### Configuración en settings.py
```python
INSTALLED_APPS = [
    # ...
    'apps.cotizaciones',  # Cotizaciones
]
```

#### URLs Configuradas
```python
# config/urls.py
path('api/', include('apps.cotizaciones.urls')),  # Cotizaciones
```

### 2. Frontend

#### Componentes Creados
```
frontend/src/
├── components/
│   └── Cotizaciones/
│       ├── CotizacionList.jsx
│       └── CotizacionForm.jsx
└── services/
    └── cotizacionesService.js
```

#### Rutas Configuradas
```javascript
// App.jsx
<Route path="cotizaciones" element={<CotizacionList />} />
<Route path="cotizaciones/nueva" element={<CotizacionForm />} />
<Route path="cotizaciones/:id/editar" element={<CotizacionForm />} />
```

#### Menú Actualizado
```javascript
// Layout.jsx
{
  name: 'Cotizaciones',
  icon: FaFileInvoice,
  path: '/cotizaciones'
}
```

## 🚀 Uso del Módulo

### Crear una Cotización
1. Ir a "Cotizaciones" en el menú lateral
2. Clic en "Nueva Cotización"
3. Seleccionar cliente
4. Ingresar asunto y descripción
5. Configurar moneda, IGV y validez
6. Agregar productos/servicios
7. Completar condiciones comerciales
8. Agregar notas y términos (opcional)
9. Guardar

### Exportar a PDF
1. En el listado de cotizaciones
2. Clic en el menú de acciones (⋮)
3. Seleccionar "Exportar PDF"
4. El PDF se descargará automáticamente

### Convertir a Venta
1. En el listado de cotizaciones
2. Clic en el menú de acciones (⋮)
3. Seleccionar "Convertir a Venta"
4. Se creará automáticamente una venta con los mismos datos

### Duplicar Cotización
1. En el listado de cotizaciones
2. Clic en el menú de acciones (⋮)
3. Seleccionar "Duplicar"
4. Se creará una copia con nuevo número

## 🎯 Personalización del Logo

### Subir Logo de la Empresa
1. Ir a "Configuración" > "Empresa"
2. Subir el logo de la empresa
3. El logo aparecerá automáticamente en todos los PDFs de cotizaciones

### Ubicación del Logo en el PDF
- **Posición**: Esquina superior izquierda
- **Tamaño**: 2 pulgadas de ancho (ajustable proporcionalmente)
- **Formato**: Cualquier formato de imagen soportado por PIL/Pillow

## 📊 Estados de Cotización

| Estado | Descripción | Color |
|--------|-------------|-------|
| **Borrador** | Cotización en proceso de creación | Gris |
| **Enviada** | Cotización enviada al cliente | Azul |
| **Aceptada** | Cliente aceptó la cotización | Verde |
| **Rechazada** | Cliente rechazó la cotización | Rojo |
| **Vencida** | Cotización fuera de validez | Naranja |
| **Convertida** | Convertida a venta | Morado |

## 🔧 Configuración Avanzada

### Personalizar Colores del PDF
Editar `backend/apps/cotizaciones/utils/pdf_generator.py`:

```python
# Colores corporativos elegantes
COLOR_PRIMARY = colors.HexColor('#2C3E50')      # Azul oscuro
COLOR_SECONDARY = colors.HexColor('#3498DB')    # Azul corporativo
COLOR_ACCENT = colors.HexColor('#E74C3C')       # Rojo
COLOR_SUCCESS = colors.HexColor('#27AE60')      # Verde
```

### Personalizar Términos y Condiciones por Defecto
Editar el modelo `Cotizacion` en `backend/apps/cotizaciones/models.py`:

```python
terminos_condiciones = models.TextField(
    blank=True,
    null=True,
    default="Términos y condiciones estándar aquí..."
)
```

### Personalizar Validez de Oferta por Defecto
Editar el modelo `Cotizacion`:

```python
validez_oferta = models.CharField(
    max_length=100,
    default='30 días'  # Cambiar según necesidad
)
```

## 📈 Estadísticas Disponibles

El endpoint `/api/cotizaciones/estadisticas/` proporciona:
- Total de cotizaciones
- Cotizaciones por estado (con porcentajes)
- Valor total de cotizaciones
- Valor de cotizaciones aceptadas
- Tasa de conversión (aceptadas / total)

## 🔒 Seguridad

- ✅ Autenticación requerida para todos los endpoints
- ✅ Multi-tenancy: Cada empresa solo ve sus cotizaciones
- ✅ Permisos por empresa (HasEmpresaPermission)
- ✅ Validaciones en backend y frontend
- ✅ Protección contra inyección SQL (Django ORM)
- ✅ Sanitización de datos

## 🐛 Solución de Problemas

### El logo no aparece en el PDF
1. Verificar que el campo `logo` en el modelo `Empresa` tenga un archivo
2. Verificar que `MEDIA_ROOT` y `MEDIA_URL` estén configurados correctamente
3. Verificar permisos de lectura en la carpeta de medios

### Error al generar PDF
1. Verificar que `reportlab` esté instalado: `pip list | grep reportlab`
2. Verificar logs del backend: `tail -f /tmp/django.log`
3. Verificar que todos los campos requeridos estén completos

### No se calculan los totales
1. Verificar que los detalles tengan `cantidad` y `precio_unitario`
2. Verificar que el método `calcular_totales()` se ejecute después de guardar detalles
3. Refrescar la página

## 📝 Mejoras Futuras Sugeridas

- [ ] Envío de cotizaciones por email
- [ ] Plantillas de cotizaciones personalizables
- [ ] Historial de cambios de estado
- [ ] Notificaciones automáticas de vencimiento
- [ ] Firma digital de cotizaciones
- [ ] Múltiples idiomas en PDF
- [ ] Comparación de cotizaciones
- [ ] Dashboard de cotizaciones con gráficos
- [ ] Exportar a Excel
- [ ] Importar cotizaciones desde Excel

## 🎉 ¡Listo para Usar!

El módulo de cotizaciones está completamente funcional y listo para producción. Incluye:
- ✅ Backend completo con API REST
- ✅ Frontend profesional con React
- ✅ Generación de PDF elegante
- ✅ Logo personalizable
- ✅ Integración con el sistema ERP
- ✅ Multi-tenancy
- ✅ Seguridad implementada

**¡Disfruta de tu nuevo módulo de cotizaciones profesional!** 🚀


