# Métricas de la landing (PostHog)

Analítica **solo en la landing** (`/landing`), **solo tras consentimiento** (Ley 29733).
El ERP no tiene PostHog. `posthog-js` se carga con `import()` dinámico al aceptar.

## Configuración

- `VITE_POSTHOG_KEY` (requerida) y `VITE_POSTHOG_HOST` como variables de entorno en Vercel.
- Session replay con `maskAllInputs: true` → todos los campos de formulario enmascarados.
- Autocapture, heatmaps y scroll depth activados (nativos de PostHog).

## Eventos que emite la landing

| Evento | Cuándo | Propiedades |
|---|---|---|
| `$pageview` / `$pageleave` | nativo | — |
| `section_viewed` | una sección entra al viewport (primera vez) | `section` |
| `section_time` | la sección sale del viewport | `section`, `seconds` |
| `cta_clicked` | clic en un CTA | `cta` (acceso_hero, ingresar_hero, acceso_nav, ingresar_nav) |
| `form_started` | primer cambio en cualquier campo | — |
| `form_field_completed` | blur de un campo con valor | `field` |
| `form_submitted` | envío exitoso | `rubro`, `tamano` |
| `form_error` | el backend rechaza | `message` |
| `video_played` | el loop del hero empieza | `where` |
| `screenshot_zoomed` | clic en una captura | `shot` |
| `identify(lead_id)` | tras registrarse | `empresa`, `rubro` |

UTM (`utm_source`, `utm_campaign`) y `referrer` se guardan además en el modelo `Lead` del backend.

## Embudo a crear en PostHog (Funnel)

1. `$pageview`
2. `section_viewed` where `section = acceso`
3. `form_started`
4. `form_submitted`

Métrica norte: **tasa pageview → form_submitted**. Secundarias: caída entre
`form_started` y `form_submitted` (fricción del formulario), y `form_error` rate.

## Dashboards sugeridos

1. **Adquisición** — pageviews por `utm_source`/`utm_campaign`, referrers, dispositivos.
2. **Embudo de lead** — el funnel de arriba + conversión por fuente UTM.
3. **Engagement de contenido** — `section_time` por `section` (qué secciones retienen),
   `screenshot_zoomed`, `video_played`, scroll depth, heatmaps del hero y de `#acceso`.
4. **Fricción del formulario** — `form_field_completed` por `field` (dónde abandonan),
   `form_error` por `message`, replays de sesiones con `form_started` sin `form_submitted`.

## Privacidad

- Banner de consentimiento: nada se inicializa hasta "Aceptar".
- `/privacidad` documenta responsable, finalidad, derechos ARCO y contacto (Ley 29733).
- Inputs enmascarados en replay; no se capturan valores de los campos.
