# Deploy Optimizado — erp.soldigem.com.pe

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERNET / DNS                          │
│         erp.soldigem.com.pe → Vercel (CDN global)          │
│         api.soldigem.com.pe → Cloud Run (southamerica-w1)  │
└───────────────────┬─────────────────────┬───────────────────┘
                    │                     │
         ┌──────────▼──────────┐ ┌────────▼────────────────────┐
         │   Vercel (CDN)      │ │   Cloud Run (backend)        │
         │   React + Vite      │ │   Django 4.2 + Gunicorn      │
         │   Bundle splits:    │ │   gthread: 2w × 4t = 8 slots │
         │   • vendor.js       │ │   + PostgreSQL (Cloud SQL)   │
         │   • chakra.js       │ │   + Upstash Redis (cache)    │
         │   • charts.js       │ │                              │
         │   assets: 1yr cache │ │   REDIS_URL = rediss://...   │
         └─────────────────────┘ └──────────────────────────────┘
```

## Performance — Antes vs Después

| Métrica | Antes | Después | Mejora |
|---|---|---|---|
| Dashboard (2da carga) | ~800ms (10+ DB queries) | ~50ms (Redis hit) | **16x** |
| Dashboard (1ra carga) | ~800ms | ~400ms (queries optimizadas) | **2x** |
| Bundle inicial | ~2MB monolítico | ~400KB (vendor + chakra + charts separados) | **5x** |
| Gunicorn slots concurrentes | 3 workers sync | 8 slots (2w × 4t gthread) | **2.7x** |
| Assets estáticos | Sin cache | 1 año CDN (immutable) | N/A |

*Baseline estimado. Medir con Chrome DevTools en staging antes del launch.*

## Costos Mensuales Estimados

| Servicio | Tier | Costo estimado |
|---|---|---|
| Cloud Run (backend) | Mínimo 0 instancias, escala a demanda | $0–$15/mes |
| Cloud SQL (PostgreSQL) | db-f1-micro | ~$10/mes |
| Upstash Redis | Free tier (10K req/día) → Pro $10/mes | $0–$10/mes |
| Vercel (frontend) | Free tier (hobby) / Pro $20/mes | $0–$20/mes |
| **Total** | | **$10–$55/mes** |

*Free tier de Upstash es suficiente para < 10K usuarios. Vercel Free es suficiente para PYME.*

## Variables de Entorno Necesarias

### Cloud Run (backend)

```bash
REDIS_URL=rediss://:<password>@<host>.upstash.io:6379
CORS_ALLOWED_ORIGINS=https://erp.soldigem.com.pe
DJANGO_ALLOWED_HOSTS=api.soldigem.com.pe,erp-backend-25656632090.southamerica-west1.run.app
DATABASE_URL=postgresql://...
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
```

### Vercel (frontend)

```bash
VITE_API_URL=https://api.soldigem.com.pe
```

## Pasos para Deploy en Vercel

### 1. Crear cuenta y conectar repositorio
```bash
# Instalar Vercel CLI
npm install -g vercel

# Desde /frontend
cd frontend
vercel login
vercel link   # conectar al proyecto
```

### 2. Configurar variables de entorno en Vercel Dashboard
Settings → Environment Variables:
- `VITE_API_URL` = `https://api.soldigem.com.pe`

### 3. Configurar dominio custom
Vercel Dashboard → Domains → Add `erp.soldigem.com.pe`
Agregar CNAME record en DNS: `erp.soldigem.com.pe` → `cname.vercel-dns.com`

### 4. Deploy
```bash
# Deploy de producción (desde /frontend)
vercel --prod

# O en CI/CD: cada push a main deploya automáticamente
```

### 5. Verificar SPA routing
```bash
curl -I https://erp.soldigem.com.pe/ventas
# Debe retornar 200, no 404
```

## Pasos para Deploy en Cloud Run

### 1. Crear Upstash Redis
1. Ir a https://console.upstash.com → Create Database
2. Región: South America (São Paulo) para latencia mínima con Cloud Run southamerica-west1
3. Copiar la `REDIS_URL` (formato `rediss://...`)
4. Agregar como secret en Cloud Run

### 2. Build y deploy
```bash
# Desde raíz del proyecto
gcloud builds submit --tag gcr.io/PROJECT_ID/erp-backend .
gcloud run deploy erp-backend \
  --image gcr.io/PROJECT_ID/erp-backend \
  --region southamerica-west1 \
  --set-env-vars REDIS_URL=rediss://...,CORS_ALLOWED_ORIGINS=https://erp.soldigem.com.pe \
  --min-instances 0 \
  --max-instances 3
```

### 3. Configurar dominio custom
Cloud Run → Custom domains → Map `api.soldigem.com.pe`

## Invalidación de Cache — Referencia

| Evento | Claves invalidadas |
|---|---|
| Crear/editar/eliminar venta | `ventas_list_{id}`, `dashboard_mes_{id}`, `dashboard_historico_{id}`, `dashboard_simple_stats_{id}` |
| Crear compra | `compras_list_{id}`, `dashboard_mes_{id}`, `dashboard_historico_{id}`, `dashboard_simple_stats_{id}` |
| Crear/editar producto | `productos_list_{id}` (via `cache_manager.invalidate_productos`) |
| Crear/editar proveedor | `proveedores_list_{id}` |
| Crear/editar categoría | `categorias_list_{id}` |

### Limpiar cache manualmente (desde Django shell)
```python
from django.core.cache import cache
cache.clear()                          # todo el cache de la empresa
cache.delete('dashboard_mes_1')        # dashboard de empresa id=1
```

## Cache TTL por Vista

| Vista | TTL | Clave |
|---|---|---|
| `DashboardResumen` | 120s | `dashboard_mes_{empresa_id}` |
| `DashboardStatsView` | 120s | `dashboard_stats_{empresa_id}_{days}` |
| `DashboardResumenView` | 120s | `dashboard_historico_{empresa_id}` |
| `get_dashboard_stats` | 120s | `dashboard_simple_stats_{empresa_id}` |
| `FinanzasDashboardView` | 300s | `finanzas:{id}:{fecha_inicio}:{fecha_fin}` |
| `VentaViewSet.list()` | 60s | `ventas_list_{empresa_id}` |
| `CompraViewSet.list()` | 60s | `compras_list_{empresa_id}` |
| `ProductoViewSet.list()` | 120s | `productos:{empresa_id}` |
| `CategoriaViewSet.list()` | 600s | `categorias_list_{empresa_id}` |
| `ProveedorViewSet.list()` | 300s | `proveedores_list_{empresa_id}` |
| Sesiones de usuario | Default Django | Redis (SESSION_ENGINE=cache) |

## Checklist Pre-Launch

- [ ] `REDIS_URL` configurada en Cloud Run secrets
- [ ] `CORS_ALLOWED_ORIGINS=https://erp.soldigem.com.pe` en Cloud Run
- [ ] `VITE_API_URL=https://api.soldigem.com.pe` en Vercel
- [ ] Dominio `erp.soldigem.com.pe` apuntando a Vercel (CNAME)
- [ ] Dominio `api.soldigem.com.pe` apuntando a Cloud Run
- [ ] Login cross-domain probado con httpOnly cookies
- [ ] Dashboard segunda carga < 1s verificado en Network tab
- [ ] `npm run build` pasa sin warnings de chunk > 1000KB
- [ ] `curl -I https://erp.soldigem.com.pe/ventas` retorna 200
- [ ] Assets con `Cache-Control: public, max-age=31536000, immutable`
