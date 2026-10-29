# ENTREGA — fix/bot-ventas-errores

Rama desde `main`. LOCAL, sin push ni deploy.

## Causas (caso real 29/10 11:29)

1. **S/ 39 en vez de USD 39**: `_precio_de` copiaba el número del catálogo a la
   moneda del documento (default PEN del esquema) y solo dejaba un aviso.
2. **Error crudo**: el producto coincidente es materia prima; el serializer de
   ventas lo rechaza y el orquestador respondía `No pude crearlo: {'detalles':
   [ErrorDetail(...)]}` tal cual.
3. Además, nada convertía el insumo en línea libre: la venta quedaba bloqueada.

## Cambios

1. **Moneda**: el número de un precio de catálogo NUNCA cambia de moneda. Si
   todo el catálogo usado coincide, el documento la **adopta** (Bruno → USD);
   si el usuario pidió otra o hay mezcla, el borrador queda incompleto y
   pregunta con botones **[S/ Soles] [$ Dólares]**; al elegir una distinta, ese
   precio se pide de nuevo. El esquema ya no tiene default PEN (moneda solo si
   el usuario la dijo: «$39» → USD, «39 soles» → PEN). Aplica a venta y
   cotización, también al elegir producto por botón.
2. **Materia prima**: nunca bloquea; entra como **línea libre** con el mismo
   nombre y precio y el aviso «“X” está registrado como insumo; lo incluyo
   como línea libre» (solo ventas; la cotización no tiene esa restricción).
3. **Errores al confirmar**: conocidos → frase en español con acción
   (insumo→línea libre, cliente/producto inválido→pedir de nuevo, stock→ajustar
   cantidad); desconocidos → «No pude crear la venta por un error interno; el
   equipo ya fue notificado» + **log ERROR** con el detalle. La transacción
   revierte: **el borrador sigue pendiente** y el reintento funciona (test).
4. **Web — líneas libres en Nueva Venta**: el backend YA lo soportaba
   (`DetalleVenta.producto` nullable + serializer, del lote anterior) →
   **solo frontend, sin migración**. `NuevaVenta.jsx`: opción «✍️ Línea libre
   (sin catálogo)» en el selector (descripción + cantidad + precio, con volver
   al catálogo); el servicio manda `producto: null`; «Modo de Venta» solo se
   muestra cuando hay productos de catálogo. Las líneas libres no mueven stock
   ni kárdex (test de regresión web: crear + entregar).

## Migraciones

**Ninguna.** `makemigrations --check`: sin cambios.

## Pruebas

- Suite completa backend en Postgres: **414 tests OK (3 skipped), 0 fallos**. Frontend: vitest
  12/12 y `vite build` OK.
- Tests nuevos (12): caso Bruno e2e (borrador USD 39 con línea libre y aviso;
  confirmación a $92.04), conflicto soles↔catálogo USD (pregunta y no copia el
  número), «$39» del usuario manda, cotización adopta moneda, errores
  desconocido/conocido con borrador reintentable, línea libre web sin stock.
- **Eval real flash-lite: 33/33 correctos** (87,810 tokens, media 2.3 s;
  umbral 30/33 y críticos ✓), incluido el **#33 con el texto exacto de Bruno**:
  borrador en USD, línea libre con aviso de insumo y condición pendiente.
