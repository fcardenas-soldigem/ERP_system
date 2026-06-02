# Purchase Orders Service

Microservicio de Órdenes de Compra para ERP System.

| Stack | Versión |
|-------|---------|
| Node.js | ≥ 18 |
| Express | 4.x |
| Prisma | 6.x |
| PostgreSQL | 15+ (Supabase) |
| PDFKit | 0.15 |
| xlsx | 0.18 |

## Setup

```bash
cd purchase-orders-service

# 1. Instalar dependencias
npm install

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales de Supabase

# 3. Generar Prisma Client
npm run db:generate

# 4. Aplicar migraciones
npm run db:migrate

# 5. Iniciar en desarrollo
npm run dev
```

El servicio corre en `http://localhost:3001` por defecto.

## Arquitectura

```
src/
├── server.js                         # Entry point
├── app.js                            # Express setup
├── config/
│   ├── index.js                      # Env config
│   └── logger.js                     # Winston
├── prisma/
│   └── client.js                     # Prisma singleton
├── common/
│   ├── exceptions/AppError.js        # Error classes
│   ├── middleware/
│   │   ├── error-handler.js          # Centralizado
│   │   ├── async-handler.js          # Wrapper async
│   │   └── validate.js               # Joi middleware
│   └── utils/
│       ├── pdf-generator.js          # PDFKit
│       └── excel-parser.js           # xlsx parser
└── modules/
    └── purchase-orders/
        ├── purchase-order.routes.js
        ├── purchase-order.controller.js
        ├── purchase-order.service.js
        ├── purchase-order.repository.js
        ├── purchase-order.validator.js
        └── dto/
            ├── create-purchase-order.dto.js
            └── update-purchase-order.dto.js
```

## API Endpoints

Base URL: `http://localhost:3001/api/purchase-orders`

### Health Check

```bash
curl http://localhost:3001/health
```

### Crear Orden de Compra

```bash
curl -X POST http://localhost:3001/api/purchase-orders \
  -H "Content-Type: application/json" \
  -d '{
    "supplierName": "Distribuidora ABC S.A.C.",
    "supplierRuc": "20123456789",
    "supplierAddress": "Av. Industrial 456, Lima",
    "supplierContact": "Juan Pérez",
    "supplierEmail": "ventas@abc.com",
    "companyName": "Soldigem S.A.C.",
    "companyRuc": "20987654321",
    "companyAddress": "Calle Los Pinos 123, Lima",
    "currency": "PEN",
    "paymentTerms": "CRE30",
    "issueDate": "2026-02-08",
    "dueDate": "2026-03-10",
    "deliveryConditions": "Entrega en almacén principal, Lunes a Viernes 9am-5pm",
    "considerations": "Material debe cumplir norma ISO 9001",
    "items": [
      {
        "description": "Tubo de acero inoxidable 1/2\" x 6m",
        "quantity": 100,
        "unit": "UND",
        "unitPrice": 45.50
      },
      {
        "description": "Válvula esférica 1/2\"",
        "quantity": 50,
        "unit": "UND",
        "unitPrice": 28.00
      },
      {
        "description": "Empaquetadura de teflón rollo",
        "quantity": 200,
        "unit": "UND",
        "unitPrice": 3.50
      }
    ]
  }'
```

### Listar Órdenes (con paginación y filtros)

```bash
# Básico
curl "http://localhost:3001/api/purchase-orders"

# Con filtros
curl "http://localhost:3001/api/purchase-orders?status=DRAFT&page=1&limit=10&sortBy=createdAt&sortOrder=desc"

# Búsqueda
curl "http://localhost:3001/api/purchase-orders?search=Distribuidora"

# Rango de fechas
curl "http://localhost:3001/api/purchase-orders?from=2026-01-01&to=2026-12-31"
```

### Obtener Detalle

```bash
curl http://localhost:3001/api/purchase-orders/{id}
```

### Actualizar Orden (solo DRAFT)

```bash
curl -X PUT http://localhost:3001/api/purchase-orders/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "supplierContact": "María López",
    "items": [
      {
        "description": "Tubo de acero inoxidable 1/2\" x 6m",
        "quantity": 150,
        "unit": "UND",
        "unitPrice": 44.00
      }
    ]
  }'
```

### Cambiar Estado

```bash
# Aprobar
curl -X PATCH http://localhost:3001/api/purchase-orders/{id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "APPROVED"}'

# Cerrar
curl -X PATCH http://localhost:3001/api/purchase-orders/{id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CLOSED"}'
```

Transiciones válidas: `DRAFT → APPROVED → CLOSED`, `APPROVED → DRAFT` (revertir).

### Eliminar (soft delete)

```bash
curl -X DELETE http://localhost:3001/api/purchase-orders/{id}
```

### Generar PDF

```bash
# Descargar
curl http://localhost:3001/api/purchase-orders/{id}/pdf -o orden.pdf

# Abrir en navegador
open "http://localhost:3001/api/purchase-orders/{id}/pdf"
```

### Importar Items desde Excel

```bash
curl -X POST http://localhost:3001/api/purchase-orders/import \
  -F "file=@items.xlsx"
```

El Excel debe tener columnas: `descripcion`, `cantidad`, `precio unitario` (u otras variantes reconocidas).

Retorna los items parseados para usar en la creación de la orden.

## Modelo de Datos

### po_purchase_orders

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID | PK |
| po_number | VARCHAR | Correlativo OC-YYYY-NNNNNN |
| supplier_* | VARCHAR | Datos del proveedor |
| company_* | VARCHAR | Datos de la empresa |
| currency | ENUM | PEN / USD |
| subtotal | DECIMAL(14,2) | Suma de items |
| igv | DECIMAL(14,2) | 18% del subtotal |
| total | DECIMAL(14,2) | subtotal + igv |
| status | ENUM | DRAFT / APPROVED / CLOSED |
| deleted_at | TIMESTAMP | Soft delete |
| empresa_id | BIGINT | Multi-tenancy (futuro) |

### po_purchase_order_items

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID | PK |
| purchase_order_id | UUID | FK → po_purchase_orders |
| description | TEXT | Descripción del item |
| quantity | DECIMAL(14,4) | Cantidad |
| unit | VARCHAR(20) | UND, KG, LT, etc. |
| unit_price | DECIMAL(14,4) | Precio unitario |
| total | DECIMAL(14,2) | quantity × unit_price |

## Decisiones de Diseño

**¿Por qué un microservicio Node.js separado?**
- Independencia total del módulo Django existente
- Las tablas usan prefijo `po_` para no colisionar con Django
- Puede desplegarse y escalarse de forma independiente

**¿Por qué Joi en lugar de class-validator?**
- `class-validator` requiere TypeScript y decoradores
- Joi es el estándar de validación para Express.js
- Misma robustez, sintaxis más natural para JavaScript

**¿Por qué PDFKit en lugar de Puppeteer?**
- PDFKit genera PDFs nativamente sin necesitar Chrome/Chromium
- Mucho más ligero (~5MB vs ~300MB de Puppeteer)
- Mejor rendimiento y menor uso de memoria

**Correlativo OC-YYYY-NNNNNN:**
- Usa tabla `po_sequences` con UPSERT atómico
- Reinicia automáticamente cada año
- Thread-safe dentro de una transacción Prisma

**Multi-tenancy:**
- Campo `empresa_id` presente pero opcional
- Preparado para agregar middleware de tenant sin cambios de schema
