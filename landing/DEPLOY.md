# Despliegue de la landing en Vercel + cutover

La landing es un **proyecto Vercel separado** del ERP. Convive bajo el mismo
dominio (`soldigem.com.pe`) gracias a los rewrites de `vercel.json`: la landing
sirve `/` y `/privacidad`; todo lo demás (`/login`, `/app/*`, `/api/*`) se
reescribe al proyecto del ERP. Así las URLs, cookies y CORS del ERP no cambian.

## 1. Crear el proyecto nuevo en Vercel

1. Vercel → **Add New → Project** → importar el mismo repositorio Git.
2. **Root Directory: `landing`** (Edit → seleccionar la carpeta `landing`).
3. Framework preset: **Vite**. Build command `npm run build`, output `dist`
   (autodetectado). Install `npm install`.
4. Nómbralo p. ej. `soldigem-landing`.

## 2. Variables de entorno (Production + Preview)

| Variable | Valor | Notas |
|---|---|---|
| `VITE_POSTHOG_KEY` | `phc_...` | Project API Key de PostHog. Sin esto, PostHog no se inicializa. |
| `VITE_POSTHOG_HOST` | `https://us.i.posthog.com` | O el host de tu instancia. |
| `VITE_API_BASE` | *(vacío)* | En prod es mismo-origen vía rewrites; dejar sin definir. |

No se define `VITE_API_BASE` en prod: el form hace `POST /api/leads/` relativo y
el rewrite lo lleva al ERP.

## 3. Verificar el rewrite al ERP

El `vercel.json` apunta el catch-all a `https://erp-system-pearl-five.vercel.app`.
Si la URL del proyecto ERP cambia, actualizar esa `destination`. Tras el deploy,
probar en la URL de preview del proyecto landing:
- `/` y `/privacidad` → sirven la landing.
- `/login` → debe cargar el login del ERP (vía rewrite).
- `/l-assets/*`, `/og.png`, `/sitemap.xml`, `/robots.txt` → estáticos de la landing.

## 4. Cutover del dominio (orden importante)

Hoy `erp.soldigem.com.pe` (o el dominio en uso) apunta al proyecto del ERP.
Para que la raíz sea la landing sin romper el ERP:

1. **Primero** desplegar la landing y validar los rewrites en su URL de preview
   (que `/login` y `/api/*` lleguen al ERP correctamente).
2. En el proyecto **ERP**, quitar el dominio público principal (seguirá
   accesible por su URL `*.vercel.app`, que es a donde apunta el rewrite).
3. En el proyecto **landing**, **añadir el dominio** (`soldigem.com.pe` y/o
   `www`). Vercel reasigna el DNS.
4. Validar en el dominio real: `/` = landing, `/login` y `/app/*` = ERP, el
   formulario crea leads, y las cookies de sesión del ERP siguen funcionando
   (mismo dominio, mismo path).
5. Rollback: si algo falla, devolver el dominio al proyecto ERP (paso inverso).

> Nota CORS: como todo queda bajo el mismo dominio, el navegador ve mismo-origen
> y no hay preflight. No se toca `CORS_ALLOWED_ORIGINS` del backend. (En
> desarrollo local sí se agregó `localhost:5173` a CORS para probar el form
> cross-origin; eso es solo dev.)

## 5. Assets de Higgsfield (pendientes)

`/l-assets/hero-poster.jpg`, `/og.png` y `/media/hero.mp4` son **placeholders**.
Reemplazarlos por los generados en Higgsfield (ver prompts en el reporte) antes
del deploy final. El video debe ir comprimido < 3 MB con su poster.
