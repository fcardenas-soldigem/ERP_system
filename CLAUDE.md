# ERP Soldigem — Guía para Claude Code

## Principios fundamentales del producto

Este ERP NO se comporta como un ERP corporativo antiguo.
La prioridad es: **simplicidad → velocidad → claridad → menos fricción**.

Antes de implementar cualquier cosa, pregunta:
- ¿Esto hace más fácil el trabajo diario del usuario?
- ¿Reduce complejidad o pasos?
- ¿Reduce tiempo operativo?
- ¿Reduce errores humanos?
- ¿Reduce curva de aprendizaje?

Si la respuesta es NO → simplificar o eliminar.

**Menos clics = mejor.**
Cada pantalla debe poder usarse sin manual.

---

## Stack técnico

**Backend:** Django + Django REST Framework + PostgreSQL
- Apps: `ventas`, `compras`, `cotizaciones`, `clientes`, `proveedores`, `produccion`, `cuentas`
- Auth: JWT (SimpleJWT), sesiones de 6 horas
- Empresa multitenant: cada objeto filtrado por `empresa = request.user.empresa`
- Serializadores anidados: los `detalles`/`items` se recrean en `update()` (delete + recreate)

**Frontend:** React + Vite + Chakra UI + React Router v6 + TanStack Query
- Rutas bajo `/app/` con lazy loading
- Servicios en `frontend/src/services/`
- Componentes por módulo en `frontend/src/components/`
- Iconos: `react-icons/fa`

**Rutas de arranque:**
```bash
# Backend
cd ~/Desktop/ERP/ERP_system
source venv/bin/activate
python manage.py runserver

# Frontend
cd frontend
npm run dev
```

---

## Convenciones de código

### Frontend
- Componentes: PascalCase, `.jsx`
- Servicios: camelCase, métodos async/await
- Siempre `stopPropagation()` en acciones dentro de filas clickeables
- Menú ⋮ (tres puntos) con Chakra `Menu/MenuButton/MenuList/MenuItem`
- Paginación: `PAGE_SIZE = 20`, parámetros `page` y `page_size`
- Estados de OC/OCS: `borrador → enviada → aprobada → rechazada/completada`
- Solo permitir "Editar" en estado `borrador` para OC; OCS sin restricción de estado

### Backend
- ViewSets con `ModelViewSet` + `permission_classes = [IsAuthenticated, HasEmpresaPermission]`
- `perform_create`: siempre inyectar `empresa=request.user.empresa`
- Acciones custom con `@action(detail=True, methods=[...], url_path='...')`
- Serializadores: campos `read_only` para `id`, `numero`, `empresa`, `fecha_creacion`

### Modo edición en formularios
Patrón estándar (ver `OrdenCompraServicioForm.jsx` y `OrdenCompraForm.jsx`):
```js
const { id } = useParams();
const esEdicion = Boolean(id);
// useEffect carga datos si esEdicion
// handleSubmit: service.update(id, payload) vs api.post(...)
// Heading/botón cambia según esEdicion
```

---

## Módulos principales

| Módulo | Lista | Formulario | Detalle |
|--------|-------|------------|---------|
| Cotizaciones | `CotizacionList` | `CotizacionForm` | `CotizacionDetalle` |
| Órdenes Compra | `OrdenesCompraList` | `OrdenCompraForm` | `OrdenCompraDetalle` |
| OC Servicio | `OrdenesServicioCompraList` | `OrdenCompraServicioForm` | `OrdenServicioCompraDetalle` |
| Ventas | — | — | — |
| Producción | `OrdenProduccionList` | `OrdenProduccionForm` | `OrdenDetalle` |

---

## Skill routing

Cuando la solicitud del usuario coincida con un skill disponible, invócalo vía la herramienta Skill.

- Bugs / errores / "por qué no funciona" → `/investigate`
- Comandos destructivos / prod / reset → `/careful`
- QA / probar que algo funciona → `/qa`
- Revisión de código / diff → `/review`
- Diseño visual / UI → `/design-review`
- Ship / PR / deploy → `/ship`
- Planificación / arquitectura → `/plan-eng-review`
- Ideas de producto → `/office-hours`

---

## Notas operacionales

- El backend corre en `http://localhost:8000`
- El frontend corre en `http://localhost:5173`
- Los PDF se generan en el backend con `reportlab` y se devuelven como blob
- Los archivos Excel de OCS usan `xlsx` en el frontend
- Multitenant: nunca omitir el filtro `empresa` en queries del backend
- Los tokens JWT expiran en 6 horas (configurado en `settings.py`)
