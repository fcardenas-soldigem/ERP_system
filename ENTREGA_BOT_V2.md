# ENTREGA — fix/bot-cotizacion-libre (bot V2)

Rama `fix/bot-cotizacion-libre`, creada desde `main` (54908a4). LOCAL, sin push
ni deploy. Correcciones a las fallas reales del piloto al cotizar por Telegram.

## 1. Causa raíz de cada falla

### a) «Me faltan datos» y luego un ítem basura «productos y cantidades» S/ 0.00
Tres causas encadenadas:
1. `PrepararCotizacion` **exigía cliente** (validator de pydantic). El mensaje 1
   traía 2 productos con precio pero sin cliente → argumentos inválidos → el bot
   respondió «Me faltan datos» y **descartó los ítems completos**.
2. El bot **no tenía memoria**: cada mensaje se interpretaba solo. En el mensaje
   2 el modelo solo vio «Cliente Uhman Perú sac / Ya te di los productos y
   cantidades» y convirtió la frase en un ítem.
3. No había **validación de meta-frases** ni **líneas libres automáticas**: el
   texto «productos y cantidades» pasó como descripción con precio nulo → S/ 0.00.

### b) Precio con IGV mal guardado
El esquema del bot no tenía forma de expresar «incluido IGV» y el resumen decía
«Subtotal aprox. + IGV». La web sí lo soporta: cuando el usuario marca «incluye
IGV», guarda el precio tal cual con `precios_incluyen_igv=True` y el modelo
extrae el IGV (`Cotizacion.calcular_totales`).

### c) DOS borradores idénticos con el mismo timestamp
- Causa verificable en el código: `TelegramCanal.recibir()` trataba
  `edited_message` **igual que un mensaje nuevo**. Un mensaje editado llega como
  update nuevo con `update_id` DISTINTO, así que la idempotencia por update_id
  (que sí funciona para los reintentos de Telegram) no lo frena: el texto
  completo se reinterpretaba y nacía un segundo borrador idéntico. Editar el
  mensaje (p. ej. corregir una tilde) tras la respuesta del bot reproduce
  exactamente «dos borradores idénticos».
- Factor agravante: no existía el invariante «un solo borrador pendiente por
  chat», así que cualquier duplicación dejaba DOS mensajes con botón «Confirmar»
  vivos.
- Descartado: el reintento por timeout de Telegram (el webhook responde 200 de
  inmediato y procesa en un hilo; además el dedup por `update_id` lo cubre y hay
  test que lo prueba). El `callback_query` repetido no crea borradores, pero se
  le agregó idempotencia propia igual.

### d) «Cuánto voy en ventas este mes» → mensaje de ayuda
No era un error técnico: **ninguna tool del bot cubría cifras del período**
(solo `consultar_venta`, de una venta puntual). El modelo no llamó ninguna
herramienta → respuesta fija de fuera de alcance. Los errores técnicos ya
tenían su camino propio («El asistente tuvo un problema…» + `logger.exception`,
severity ERROR); hay test que distingue ambos casos.

## 2. Cambios

### Punto 1 — Líneas libres (sin catálogo)
- **Modelo**: `DetalleCotizacion.producto` **ya era nullable** con `descripcion`
  libre (migración previa de D1) → **no hizo falta migración** aquí.
- `ItemCotizacion` acepta `descripcion` (texto completo y largo), mantiene
  `producto` como alias, y agrega `precio_incluye_igv`.
- `_resolver_item`: sin match en catálogo y **con precio → línea libre directa**
  (`estado='libre'`, `producto=None`), sin botón intermedio. El botón «usar como
  texto libre» queda solo para match dudoso (ambiguo) o ítems sin precio. El
  umbral del match sigue siendo alto: TODAS las palabras del usuario deben
  coincidir para resolver a un producto.
- Meta-frases («productos y cantidades», «ya te di…», «lo que te dije», «los
  mismos») se filtran; si no queda ningún ítem real, el bot pide aclaración y
  **no crea nada**.
- Conversión a venta: ya trataba `producto=None` como `pedido_proveedor` y
  `Venta._debe_mover_stock()` exige producto; test nuevo prueba que una línea
  libre **no mueve stock ni kárdex** ni al convertir ni al entregar.
- **Formulario web: verificado, YA permite líneas libres** (envía
  `producto: d.producto || null` con descripción editable; el detalle muestra
  `producto_nombre || descripcion` y el PDF usa `descripcion`). Nada que
  implementar ni reportar como faltante.

### Punto 2 — Precio con IGV
- Igual que la web: si TODOS los precios del usuario incluyen IGV →
  `precios_incluyen_igv=True` y se guardan tal cual. 4 × 441.00 + 1 × 1750.00 =
  **S/ 3,514.00 exacto** (IGV extraído: 536.03). Si se mezclan con precios base
  (catálogo o sin IGV), los que incluían IGV se convierten a base ÷1.18
  (2 decimales) con aviso en la línea, y el flag queda en False.
- El borrador muestra `Subtotal · IGV (18%) · Total`, sin «+ IGV».

### Punto 3 — Contexto conversacional
- Nuevo `MensajeConversacion` (migración `canales.0002`, aditiva): memoria corta
  por chat (user/assistant), scoped a empresa+usuario.
- `nucleo/contexto.py` (compartido por bot y eval): historial de los últimos
  `CANALES_HISTORIAL_MENSAJES` (por defecto **10**, configurable) con tope
  `CANALES_HISTORIAL_MAX_CHARS` (4000, proxy de tokens; 600 por mensaje), más el
  **borrador pendiente compacto** (sin claves de trabajo).
- Si falta el cliente, el borrador **se crea igual** con los ítems y el bot
  pregunta SOLO «¿Para qué cliente es la cotización?».
- Un seguimiento («Cliente X», «cámbiale la cantidad a 6», «quita el gabinete»)
  **edita el borrador pendiente**: el modelo re-llama la tool con todos los
  datos y el nuevo borrador desplaza al anterior; ya no hace falta el botón
  «Editar» (que sigue funcionando).

### Punto 4 — Borradores duplicados
- `edited_message` se ignora (causa raíz, ver §1c).
- **Un solo borrador pendiente por chat**: al crear uno nuevo, los pendientes
  anteriores pasan a estado **«reemplazado»** y a su mensaje viejo se le quitan
  los botones (`editMessageReplyMarkup`; `sendMessage` ahora devuelve el
  `message_id` y se guarda en el payload).
- Idempotencia por `update_id` (existente, con test) **y** por
  `callback_query.id` (nueva, caché 1 h).
- El webhook ya respondía 200 rápido y procesa en hilo (gthread); no se metieron
  colas. Nota operativa: en Cloud Run el CPU se congela tras responder si no hay
  `--no-cpu-throttling`; el job actual ya lo contempla (DEPLOY.md §11).

### Punto 5 — resumen_ventas
- Nueva tool de LECTURA `resumen_ventas(periodo: mes|mes_anterior)`: total del
  mes vs el anterior, nº de ventas, top 3 clientes y total por cobrar. Montos
  consolidados a S/ con el TC guardado por documento (`desglose_pen`, un solo
  lookup de TC de fallback), filtrado por `usuario.empresa`; al ser lectura,
  disponible también para rol `solo_lectura` (como las demás consultas).
- El fallback de ayuda queda solo para mensajes sin relación con el ERP; un
  error técnico responde «tuve un problema, intenta de nuevo» y registra el
  error con severity ERROR (test `test_error_tecnico_no_es_mensaje_de_ayuda`).

## 3. Migraciones (con su SQL)

Una sola, **aditiva**: `canales/0002_memoria_chat_y_borrador_reemplazado.py`
(también suma el choice «reemplazado» a `BorradorAgente.estado`; choices no
generan SQL).

```sql
BEGIN;
-- Alter field estado on borradoragente
-- (no-op)
-- Create model MensajeConversacion
CREATE TABLE "canales_mensajeconversacion" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "canal" varchar(20) NOT NULL, "id_externo" varchar(64) NOT NULL, "rol" varchar(10) NOT NULL, "texto" text NOT NULL, "created_at" timestamp with time zone NOT NULL, "empresa_id" bigint NOT NULL, "usuario_id" bigint NOT NULL);
ALTER TABLE "canales_mensajeconversacion" ADD CONSTRAINT "canales_mensajeconve_empresa_id_44dec106_fk_empresas_" FOREIGN KEY ("empresa_id") REFERENCES "empresas_empresa" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "canales_mensajeconversacion" ADD CONSTRAINT "canales_mensajeconve_usuario_id_85053524_fk_authentic" FOREIGN KEY ("usuario_id") REFERENCES "authentication_customuser" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "canales_mensajeconversacion_empresa_id_44dec106" ON "canales_mensajeconversacion" ("empresa_id");
CREATE INDEX "canales_mensajeconversacion_usuario_id_85053524" ON "canales_mensajeconversacion" ("usuario_id");
CREATE INDEX "canales_men_usuario_268f31_idx" ON "canales_mensajeconversacion" ("usuario_id", "id_externo", "created_at" DESC);
COMMIT;
```

Riesgo en prod: nulo (solo CREATE TABLE nueva). `makemigrations --check`: sin
cambios pendientes.

## 4. Evals

Los 6 casos pedidos se agregaron al **eval del bot**
(`apps/canales/eval/mensajes.py`, casos 21–26), no a `evals/preguntas.yaml`:
ese YAML es el eval del asistente **web** (`eval_llm`), cuyas tools
(`analizar_ventas`, `buscar_productos`…) no incluyen `preparar_cotizacion` ni
soportan turnos; los casos habrían fallado por diseño. El runner del bot ganó
soporte **multi-turno** (historial + borrador pendiente, el mismo
`nucleo/contexto.py` que producción).

| # | Caso | Espera |
|---|------|--------|
| 21 | Mensaje 1 EXACTO del piloto (multilínea, IGV, sin cliente) | borrador con 2 líneas libres, `precios_incluyen_igv`, pregunta por el cliente |
| 22 | Seguimiento «Cliente Uhman Perú sac…» | completa el MISMO borrador (ítems intactos) |
| 23 | «ya te di los productos» sin borrador previo | pide aclaración, ningún ítem basura |
| 24 | «cuánto voy en ventas este mes» | usa `resumen_ventas` |
| 25 | «cámbiale la cantidad del pedestal a 6» | edita el borrador (pedestal 6, gabinete 1) |
| 26 | producto que SÍ está en catálogo | usa el producto, no línea libre |

Umbral nuevo: **≥ 90 %** de casos correctos **y ningún caso crítico fallando**
(críticos = los que crearían datos incorrectos: 21, 22, 23, 25, 26).

- **Oráculo (sin red): 26/26 correctos** — valida dataset, fixture y chequeos
  (`test_eval.py::test_oraculo_saca_todo_correcto`).
- **Eval real (punto 6): BLOQUEADO en esta máquina** — el ADC de gcloud está
  vencido (`RefreshError: Reauthentication is needed`). Tras reautenticar
  (`gcloud auth application-default login`), correr:

  ```bash
  cd backend
  LLM_PROJECT=erp-system-468516 LLM_MODEL=gemini-3.1-flash-lite \
    ../venv/bin/python manage.py eval_agente
  LLM_PROJECT=erp-system-468516 LLM_MODEL=gemini-3.1-flash \
    ../venv/bin/python manage.py eval_agente
  ```

  El comando imprime por caso: correcto/parcial/incorrecto, rondas, latencia y
  tokens, y al final los totales para comparar aciertos, rondas, tokens y costo.

Precios de referencia (agregadores de terceros, verificar en la página oficial
de Vertex): gemini‑3.1‑flash‑lite ≈ **$0.25 / $1.50** por 1M tokens
entrada/salida; para gemini‑3.1‑flash no hay precio publicado consistente (el
tier flash de Gemini 3 aparece ≈ $0.50 / $3.00, o sea ~2× el de lite). Con el
volumen del bot (~1 tool-call corta por mensaje, decenas de mensajes/día), la
diferencia es de centavos/día; **no cambiar el modelo de prod** salvo que el
eval muestre una brecha clara de aciertos en los casos críticos.

## 5. Tests

- Nuevos: `apps/canales/tests/test_cotizacion_libre.py` (22 tests que
  reproducen el caso real de punta a punta).
- Ajustados: `test_borradores` (cancelado → reemplazado), `test_resolucion_texto`
  (línea libre directa con precio + flujo con botón sin precio), `test_eval`
  (26 casos, umbral 90 %, oráculo multi-turno), `tests/base.py` (callback ids
  únicos, como en Telegram real).
- Suite del app `canales`: **99/99 OK** en Postgres.
- Suite completa del backend en Postgres: **374 tests OK (3 skipped), 0 fallos**.

## 6. Archivos modificados

Backend (rama `fix/bot-cotizacion-libre`, 6 commits):
- `apps/canales/nucleo/esquemas.py` — descripcion/precio_incluye_igv; cliente opcional; ResumenVentas
- `apps/canales/nucleo/servicios.py` — línea libre directa, meta-frases, IGV, totales, cliente «falta», resumen_ventas
- `apps/canales/nucleo/interprete.py` — tool resumen_ventas + prompt con contexto
- `apps/canales/nucleo/orquestador.py` — historial, borrador como contexto, reemplazo, callback idempotente, formato resumen
- `apps/canales/nucleo/contexto.py` — NUEVO: memoria corta compartida bot/eval
- `apps/canales/models.py` + `migrations/0002_…` — MensajeConversacion, estado «reemplazado»
- `apps/canales/base.py`, `apps/canales/telegram.py` — message_id, editar_botones, edited_message ignorado
- `apps/canales/vistas.py` — dedup en atomic propio
- `apps/canales/eval/mensajes.py`, `eval/runner.py`, `management/commands/eval_agente.py` — casos 21-26, multi-turno, umbral
- `apps/canales/tests/` — base, test_borradores, test_resolucion_texto, test_eval, test_cotizacion_libre (nuevo)
- `config/settings.py` — CANALES_HISTORIAL_MENSAJES / _MAX_CHARS

Frontend: **sin cambios** (el formulario web ya soporta líneas libres).
