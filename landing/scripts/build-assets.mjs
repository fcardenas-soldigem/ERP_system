// Pipeline de assets de la landing (Dirección A).
//
// Toma las fuentes crudas generadas en Higgsfield (ver landing/ASSETS.md) y
// produce los archivos finales optimizados que consume la web:
//   - hero-bg.webp / .avif   (A1)   fondo del hero + fallback
//   - section-texture.webp   (A2)   textura sutil de secciones
//   - og.png                 (A3 + wordmark compuesto por código)
//   - hero-poster.jpg        (primer frame del video A4)
//   - hero.mp4 / hero.webm   (A4)   loop del hero (sin audio, web-optimizado)
//
// Uso:  node scripts/build-assets.mjs
// Requiere (dev, instalados con --no-save): sharp, ffmpeg-static.
// Las fuentes crudas se leen de scripts/../.asset-tmp/ (no se commitean).

import sharp from 'sharp';
import ffmpegPath from 'ffmpeg-static';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = path.join(root, '.asset-tmp');
const pub = path.join(root, 'public');
const mediaDir = path.join(pub, 'media');
const lAssets = path.join(pub, 'l-assets');
fs.mkdirSync(mediaDir, { recursive: true });

const S = (p) => path.join(src, p);
const P = (...p) => path.join(pub, ...p);

const log = (msg) => console.log(`• ${msg}`);
const kb = (p) => `${Math.round(fs.statSync(p).size / 1024)} KB`;

// ── A1 — fondo hero (webp + avif, resolución nativa 2688×1536) ──────────────
await sharp(S('a1-hero-bg.png')).webp({ quality: 80 }).toFile(P('media', 'hero-bg.webp'));
await sharp(S('a1-hero-bg.png')).avif({ quality: 50 }).toFile(P('media', 'hero-bg.avif'));
log(`hero-bg.webp (${kb(P('media', 'hero-bg.webp'))}) + .avif (${kb(P('media', 'hero-bg.avif'))})`);

// ── A2 — textura de sección (webp) ──────────────────────────────────────────
await sharp(S('a2-section.png')).webp({ quality: 78 }).toFile(P('media', 'section-texture.webp'));
log(`section-texture.webp (${kb(P('media', 'section-texture.webp'))})`);

// ── A3 — OG 1200×630 con wordmark compuesto por código ──────────────────────
const OG_W = 1200, OG_H = 630;
const brand = '#2B5EA7';
const ink100 = '#e8edf4';   // casi blanco
const ink300 = '#94a3b8';   // gris medio para el subtítulo

// Lockup (marca "S" + wordmark + subtítulo) sobre la zona oscura derecha.
const lockup = Buffer.from(`
<svg width="${OG_W}" height="${OG_H}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .wm { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; font-weight: 700; }
    .st { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; font-weight: 500; }
  </style>
  <!-- marca -->
  <rect x="604" y="250" width="92" height="92" rx="20" fill="${brand}"/>
  <text x="650" y="314" class="wm" font-size="58" fill="#ffffff" text-anchor="middle">S</text>
  <!-- wordmark -->
  <text x="716" y="312" class="wm" font-size="56" fill="${ink100}">Soldigem ERP</text>
  <!-- subtítulo -->
  <text x="606" y="392" class="st" font-size="30" fill="${ink300}">El back-office B2B que se cierra solo</text>
</svg>`);

await sharp(S('a3-og.png'))
  .resize(OG_W, OG_H, { fit: 'cover', position: 'left' })
  // Oscurece un pelo el glow para que el azul no sature el thumbnail.
  .composite([
    { input: Buffer.from(`<svg width="${OG_W}" height="${OG_H}"><rect width="${OG_W}" height="${OG_H}" fill="black" opacity="0.18"/></svg>`), top: 0, left: 0 },
    { input: lockup, top: 0, left: 0 },
  ])
  .png()
  .toFile(P('og.png'));
log(`og.png (${kb(P('og.png'))})`);

// ── A4 — poster (primer frame) ──────────────────────────────────────────────
const frameTmp = S('_frame.png');
execFileSync(ffmpegPath, ['-y', '-i', S('a4-hero.mp4'), '-vframes', '1', frameTmp], { stdio: 'ignore' });
await sharp(frameTmp).jpeg({ quality: 82, progressive: true }).toFile(P('l-assets', 'hero-poster.jpg'));
log(`hero-poster.jpg (${kb(P('l-assets', 'hero-poster.jpg'))})`);

// ── A4 — mp4 web-optimizado (remux faststart, sin re-encode, sin audio) ─────
execFileSync(ffmpegPath, [
  '-y', '-i', S('a4-hero.mp4'), '-an', '-c:v', 'copy', '-movflags', '+faststart',
  P('media', 'hero.mp4'),
], { stdio: 'ignore' });
log(`hero.mp4 (${kb(P('media', 'hero.mp4'))})`);

// ── A4 — webm VP9 (alternativa más liviana, sin audio) ──────────────────────
execFileSync(ffmpegPath, [
  '-y', '-i', S('a4-hero.mp4'), '-an', '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '36',
  '-row-mt', '1', '-pix_fmt', 'yuv420p', P('media', 'hero.webm'),
], { stdio: 'ignore' });
log(`hero.webm (${kb(P('media', 'hero.webm'))})`);

fs.rmSync(frameTmp, { force: true });
console.log('\n✓ Assets construidos en landing/public/');
