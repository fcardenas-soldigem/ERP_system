# Assets de la landing — Dirección A

Concepto: **"El back-office que se cierra solo"**. Oscuro, estilo Linear/Vercel,
azul de marca `#2B5EA7` sobre negro. **Nunca** personas, **nunca** texto dentro
de la imagen (el wordmark del OG se compone por código).

Generados con Higgsfield (MCP `higgsfield`). Para cada asset se consulta el costo
real (`get_cost`) **antes** de generar. Tope 250 créditos, parar en 230. Máximo
1 reintento por asset.

## Registro de generación

| Asset | Descripción | Modelo | Aspect/Res | Créditos | Archivo resultante |
|-------|-------------|--------|-----------|----------|--------------------|
| A1 | Fondo hero | `recraft_v4_1` (2k) | 16:9 · 2688×1536 | 8.00 | `public/media/hero-bg.webp` (53 KB) + `.avif` (26 KB) |
| A2 | Textura de sección | `recraft_v4_1` (1k) | 16:9 · 1344×768 | 1.25 | `public/media/section-texture.webp` (33 KB) |
| A3 | Fondo OG (+ wordmark por código) | `recraft_v4_1` (1k) | 16:9→1200×630 | 1.25 | `public/og.png` (332 KB) |
| A4 | Video loop del hero | `seedance_2_0_mini` (720p, sin audio) | 16:9 · 1280×720 · 5s | 5.00 | `public/media/hero.mp4` (2.49 MB) + `hero.webm` (907 KB) |
| — | Poster del hero | primer frame de A4 (ffmpeg) | 1280×720 | 0 | `public/l-assets/hero-poster.jpg` (78 KB) |

**Total: 15.50 créditos.** Balance antes: **948.88** · Balance después: **933.38**.

> Nota: se evaluó Wan para el video, pero "Wan 3.0" no existe en el catálogo (el
> más reciente es `wan2_7`) y las generaciones ilimitadas/gratis no están
> disponibles por MCP en esta cuenta (`unlim.available: false`; Wan 2.7 costaría
> 7.5 cr). Se usó `seedance_2_0_mini`, el modelo más barato con calidad aceptable.

### IDs de generación (Higgsfield)

| Asset | job_id |
|-------|--------|
| A1 | `827015d9-9f2a-46ae-a70e-3ca695f4977f` |
| A2 | `1c78966e-71d7-49c8-b3b0-92913402e18a` |
| A3 | `bc17360a-62dd-4adc-82a3-79cb6581bd17` |
| A4 | `acb8260c-2dc5-4e3c-95e2-6581cb494209` |

Reconstrucción de los archivos finales desde las fuentes: `node scripts/build-assets.mjs`.

## Prompts exactos

**A1 — Fondo hero** (imagen, 16:9, máx. resolución disponible)
> dark abstract gradient mesh, deep navy blue #2B5EA7 fading to pure black,
> subtle thin grid lines, soft light bloom in the top-right corner, minimal,
> premium software aesthetic, no text, no people

**A2 — Textura de sección** (imagen, 16:9)
> very subtle dark noise texture with a faint blue grid pattern, near-black
> background, ultra minimal, seamless, no text, no people

**A3 — Fondo OG** (imagen, 1200×630 / 1.91:1)
> dark minimal background, deep navy #2B5EA7 glow from the left side fading to
> black, subtle grid, empty space on the right for a logo, no text, no people

El wordmark "Soldigem ERP" + subtítulo se componen **encima por código** (sharp),
con Inter.

**A4 — Video loop del hero** (video, 16:9, 5-6 s, sin audio)
> slow flowing light ribbons in deep navy blue #2B5EA7 over a pure black
> background, subtle grid, smooth gentle motion, seamless loop, no people,
> no text, minimal

Poster = primer frame del A4 extraído con ffmpeg (no se genera). Video comprimido
a < 3 MB (H.264 MP4 + WebM), sin audio.

## Uso en el código

- `hero-bg.webp` — detrás del video del hero y fallback si el video no carga o con
  `prefers-reduced-motion`.
- `section-texture.webp` — fondo sutil en secciones oscuras donde aporte (no en todas).
- `og.png` — meta `og:image` / `twitter:image`.
- `hero.mp4` + `hero.webm` + `hero-poster.jpg` — video loop de fondo del hero.
