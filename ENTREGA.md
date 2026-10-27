# ENTREGA — Bloque 0 (fix/review-movil) + Bloque 1 (feat/agente-canales)

Fecha: 2026-10-27 · Todo LOCAL, sin push ni deploy. Base: `main` (d49eac4).
Cadena: `main` → `fix/review-movil` (15 commits) → `feat/agente-canales` (4 commits).

---

## Rama `fix/review-movil` (Bloque 0)

### Commits (orden cronológico)

| Punto | Commit | Qué hace |
|---|---|---|
| prereq | 88ba181 | La cadena de migraciones de compras vuelve a aplicar en BD limpia (la suite no podía correr en Postgres, ni en main) |
| 0.1 | 48edc29 | Permisos por rol: admin / operador / solo_lectura + router-walk 100 % 403 |
| 0.2/QW1 | dfc463b | Detalle de cotización muestra cliente e ítems (+ vitest como runner del frontend) |
| 0.3 | 9b94e68 | Cookie de refresh SameSite=Lax + Domain → la sesión sobrevive en iPhone |
| 0.4 | 965cc94 | Fuera el polling (CxC, CxP, Inventario ×2, Resumen ×3, Dashboard producción) |
| QW2 | e697fff | Filas tocables en Ventas y Cotizaciones |
| QW3 | d2f56ce | Detalle de venta: cobrado, saldo y «Registrar cobro» |
| QW4 | e2a468e | El cobro hereda la moneda y precarga el saldo + «Cobrar todo» |
| QW5 | 7c7383d | Error de red en login ≠ «Credenciales inválidas» |
| QW6 | a0de650 | Tras guardar cotización → detalle |
| QW7 | 1385400 | Jorge: errores visibles, negritas, sin toasts duplicados |
| QW8 | cb784ed | Preguntas de ejemplo de Jorge como chips |
| QW9 | 8651c8c | Inicio con error → «Reintentar», no ceros |
| QW10 | 8879ba2 | Etiquetas 12 px / gris 600 (AA) |
| 0.6 | 7e55478 | xlsx (143 KB gz) y recharts (88 KB gz) bajo demanda |

**0.7 (sin commit, solo datos locales):** se eliminó COT-00000006 (+3 detalles),
el cobro de prueba USD 100 en V-000002 (pagos_total recalculado a 6 371,68 por la
señal post_delete), V-000001 volvió a «comprado» (el modelo restaura stock al
salir de «entregado») con su historial de prueba borrado, 2 conversaciones de
Jorge (+3 mensajes) y el usuario `qa-movil@local.test`.

### Suite
- Backend: **247 tests OK** (3 skips) en Postgres local (BD de test creada desde cero).
- Frontend: **vitest 8 tests OK** (nuevo runner; jest de CRA no transforma Vite) + `vite build` OK.

### Migraciones de la rama
| Migración | Reversible | NOT NULL nuevos |
|---|---|---|
| compras 0002/0003/0007/0009 (reparadas) | igual que antes; 0009 ahora usa `ADD COLUMN IF NOT EXISTS` | ninguno |
| authentication 0003_simplificar_roles | **Sí con pérdida**: reverso mapea solo_lectura→readonly y operador→comercial (el matiz original de los 5 roles viejos no se recupera) | ninguno (rol ya existía con default) |

**OJO antes del deploy:** 0003 reescribe `rol` de usuarios existentes
(readonly→solo_lectura, el resto no-admin→operador). Revisar en prod:
`SELECT rol, count(*) FROM authentication_customuser GROUP BY rol;` — cualquier
usuario que deba quedar como administrador debe tener `rol='admin'` ANTES de
que la gente trabaje (el default nuevo es operador, no admin).

### Riesgos
1. **RolEscritura cambia comportamiento en prod:** usuarios hoy `readonly`
   (default viejo) pasan a `solo_lectura` y PIERDEN las escrituras que
   (indebidamente) podían hacer. Es el objetivo, pero puede «romper» el flujo
   de alguien que operaba con el default — asignar roles antes del deploy.
2. **Cookie nueva:** tras 0.3, las sesiones activas ven un (1) login extra
   (la cookie vieja host-only no renueva). Ver DEPLOY.md §10.
3. Las migraciones de compras reparadas se validaron contra BD limpia Y contra
   el esquema real (diff de columnas idéntico), pero el deploy debe correr
   `migrate` con el Job habitual antes de mover tráfico.

### Qué probar a mano (Bloque 0)
- Con un usuario `solo_lectura`: no ve FAB/botones de crear; un POST manual a
  /api/ventas/ devuelve 403.
- Detalle de una cotización de productos: cliente + ítems visibles (web y móvil).
- Registrar un cobro sobre venta en USD: formulario llega en $ con el saldo.
- iPhone real (tras deploy con DEPLOY.md §10): login → cerrar PWA → reabrir →
  sigue dentro.
- "Por cobrar" abierta 2 min: 0 peticiones en reposo (DevTools).

---

## Rama `feat/agente-canales` (Bloque 1)

### Commits
| Punto | Commit | Qué hace |
|---|---|---|
| A1–A3 | 1c39a24 | App canales: interfaz Canal, TelegramCanal, WhatsAppCanal (TODO), webhook con secreto+idempotencia+hilo, vinculación por código, comando telegram_set_webhook |
| A4+B5–B9 | 549343d | Núcleo: 8 servicios pydantic acotados por empresa, intérprete LLM (tool-calling), orquestador con borradores+botones, transcripción de audio, fotos→GCS, límites |
| A3 front | aa23518 | «Vincular Telegram» en Configuración |
| C10–C11 | 56aee27 | 23 tests (Telegram y LLM mockeados) + eval de 15 mensajes con `manage.py eval_agente` |
| fix | 55e8d53 | Esquemas de tools sin $ref (Vertex los rechaza) |
| REVIEW #1#2#8#9 | 4856dd2 | RolEscritura en importador/core/empresas/tokens + router-walk ampliado + vistas muertas fuera |
| REVIEW #3-#13 | 66e881c | Carrera de doble confirmación (lock), foto del comprobante, transición cot:enviada, límites para no vinculados, truncado, callbacks forjados, escape HTML |
| schemas | 1f00bc8 | Sanitizador único de schemas para Gemini (exclusiveMinimum→minimum) + test con FunctionDeclaration real |
| 0.3 rev. | 2355207 | Sesión iPhone por mismo origen (rewrite /api/ en Vercel) |
| eval p1 | 1cb8ff2 | preparar_cotizacion con cliente e ítems en texto; el servidor resuelve (búsqueda difusa) y pregunta lo ambiguo con botones |
| eval p2 | b43c02b | buscar_producto absorbe consultar_stock (precio, stock, último costo, proveedor) |
| eval p3 | 3922f21 | Bucle de tools compartido bot/eval + eval_agente de punta a punta |
| eval p4 | 83c7b37 | 5 casos difíciles (20 en total) |

### Suite (tras las correcciones de la revisión)
- Backend: **283 tests OK** (3 skips) en Postgres (36 de canales).
- Frontend: vitest 8 OK + build OK.

### Migraciones
| Migración | Reversible | NOT NULL |
|---|---|---|
| canales 0001_initial | Sí (solo crea tablas nuevas) | solo en tablas nuevas (sin impacto en datos existentes) |

### Diseño en una línea por regla dura
- **La IA nunca escribe sin confirmación:** toda escritura pasa por
  `BorradorAgente` (expira a los 30 min) y nace solo en el callback
  `b:<id>:ok` → `confirmar_borrador()` (único punto de escritura).
- **Roles:** el bot respeta 0.1 — `solo_lectura` consulta; preparar/confirmar
  responde el mensaje de solo lectura.
- **Tenant:** la empresa sale SIEMPRE del usuario vinculado al chat; los
  servicios filtran por `usuario.empresa` en servidor; los borradores se
  buscan por `usuario` + `empresa`.
- **Un solo mensaje por respuesta**, con botones Confirmar/Editar/Cancelar.
- **Fuera de alcance → respuesta fija** (sin chat abierto).
- **Límites:** 60 mensajes/usuario/hora; mensajes y tokens por empresa+canal
  (`CANALES_LIMITE_MENSAJES_EMPRESA_DIA`, `CANALES_LIMITE_TOKENS_EMPRESA_DIA`).

### Riesgos
1. **Proceso en hilo (WSGI):** el webhook responde 200 y procesa en un hilo
   daemon del worker gthread. Si Cloud Run mata la instancia en ese instante,
   ese update se pierde (el usuario reintenta; la idempotencia evita
   duplicados pero no reprocesa). Mitigación futura: cola (Cloud Tasks).
2. **Link firmado del PDF:** quien tenga el link puede ver ese PDF durante
   72 h (diseño: se comparte por WhatsApp/Telegram). Caduca y no es adivinable
   (TimestampSigner + SECRET_KEY).
3. **Calidad del intérprete:** el eval (C11) corre contra Vertex real; en
   local no hay credenciales — correrlo en prod/staging antes de invitar
   usuarios (umbral 18/20: el mismo ≈ 87 % de 13/15).
4. **Costo LLM:** limitado por B9; revisar los contadores la primera semana
   (la atomicidad fina de los contadores llega con Redis en prod).
5. WhatsApp es solo esqueleto: no exponer todavía.
6. **Antes de activar `LLM_WRITE_TOOLS` (asistente web):** añadir chequeo de
   rol por usuario (REVIEW_BOT #6); hoy el flag está en false.
7. **El link del PDF es un bearer link por diseño** (se comparte con el
   cliente final): quien lo tenga ve ese PDF durante 72 h.

### Orden de deploy (cuando toque; HOY NO se despliega)
1. Deploy normal de `fix/review-movil` (migrate job → canary) con las
   variables de DEPLOY.md §10 (mismo origen: `VITE_API_URL` vacío, `VITE_API_UPLOAD_URL`, `erp.soldigem.com.pe` en `DJANGO_ALLOWED_HOSTS`).
   Asignar roles admin en prod ANTES (ver arriba).
2. Deploy de `feat/agente-canales` (migrate: solo tablas nuevas).
3. Variables nuevas del bot en Cloud Run (TG_BOT_TOKEN y TG_WEBHOOK_SECRET
   como **secretos** en Secret Manager, nunca en texto plano):
   `TG_BOT_TOKEN`, `TG_WEBHOOK_SECRET` (openssl rand -hex 32),
   `TG_BOT_USERNAME`, `API_BASE_URL=https://erp.soldigem.com.pe` (default).
4. Activar el webhook (una vez, desde cualquier máquina con los env):
   `python manage.py telegram_set_webhook --url https://erp-backend-25656632090.southamerica-west1.run.app` (Cloud Run directo; el comando rechaza otros hosts)
   (registra URL + secret + comandos; `--borrar` lo revierte).
5. Eval de punta a punta: `python manage.py eval_agente` (≥18/20 correctos para abrir
   el piloto). Corre el bucle real sobre la empresa de seed_demo en una
   transacción que se revierte; reporta por caso correcto/parcial/incorrecto,
   rondas, latencia y tokens. Último resultado real conocido (eval anterior,
   gemini-3.1-flash-lite): 11/15 — los 4 fallos eran de diseño y están
   corregidos (puntos 1–3); falta re-correrlo contra Vertex.
6. Piloto: cada usuario entra a Configuración → «Vincular Telegram».

### Qué probar a mano (Bloque 1)
- Vincular desde Configuración; `/start CODIGO` en el bot → «✅ vinculado».
- «¿ya pagó <cliente>?» → estado y saldo correctos.
- «cotízale 2 <producto> a <cliente>» → resumen + botones; Confirmar → número
  + PDF (el link abre sin sesión) + «Marcar como enviada».
- Editar: «que sean 5» corrige el borrador anterior (queda cancelado).
- Esperar 31 min y Confirmar → «expiró».
- Audio de voz con lo mismo → igual resultado.
- Foto después de confirmar un cobro → comprobante adjunto en el pago.
- Con un usuario solo_lectura: consultas sí, «registra un cobro» → mensaje de
  solo lectura.

### Datos que salen a Vertex (Gemini)
- **Texto del mensaje** del usuario (y el payload del borrador cuando pide
  editar) + el catálogo de herramientas (nombres/esquemas, sin datos).
- **Audio completo** del mensaje de voz (para transcribirlo).
- **Resultado compacto de las búsquedas intermedias** (bucle de tools, máx.
  5 rondas): si el modelo llama `buscar_cliente` o `buscar_producto` como paso
  previo, recibe SOLO `id` + `nombre` (+ `sku` en productos) de hasta 3
  coincidencias, para decidir el siguiente paso
  (`interprete._para_modelo`, con test). Precios, costos, proveedores, stock,
  teléfonos y saldos NO salen por esta vía.
- NUNCA salen: contraseñas, tokens, la base de clientes/ventas completa. Las
  consultas terminales (`consultar_venta`, `ventas_detenidas`) cortan el
  bucle y su resultado se formatea en el servidor, sin pasar por el modelo.
- Las fotos NO van a Vertex: van a GCS del proyecto como comprobante.
- Proveedor y región: `LLM_PROVIDER=vertex` (ADC del servicio), misma
  configuración que el asistente Jorge.

### Tokens y secretos
- `TG_*` en local: solo `backend/.env.local` (gitignored) con valores de
  prueba. El token real del bot y el secreto del webhook viven en Secret
  Manager de prod. La suite mockea la API de Telegram: ningún test llama a
  api.telegram.org.

---

## Revisión independiente

`REVIEW_BOT.md` — informe íntegro del subagente con contexto limpio que revisó
el diff de ambas ramas buscando escrituras sin chequeo de rol, acciones del bot
sin confirmación y fugas entre empresas.
