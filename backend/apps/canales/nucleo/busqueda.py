"""
Búsqueda difusa de clientes y productos por TEXTO libre (puntos 1 y 2).

El vendedor escribe «3 monitores lg», «inalambrico», «logitec»: un icontains
no encuentra «Monitor LG…», «inalámbrico» ni «Logitech». Aquí se normaliza
(minúsculas, sin tildes ni puntuación), se descartan palabras vacías, cada
palabra se reduce a su raíz singular y se compara por palabra con tolerancia
a un error de tipeo.

Resultado de `resolver_*`:
    ('ok', [candidato])            una sola coincidencia completa
    ('ambiguo', [hasta 3])          varias coincidencias completas
    ('no_encontrado', [hasta 3])    ninguna completa; sugerencias parciales

Se trabaja en Python sobre (id, texto) de la empresa: escala pyme (miles de
filas), sin extensiones de Postgres (unaccent/trigram).
"""
import difflib
import re
import unicodedata

MAX_OPCIONES = 3

_VACIAS = {
    'a', 'al', 'de', 'del', 'el', 'la', 'las', 'lo', 'los', 'y', 'e', 'o', 'u',
    'en', 'con', 'para', 'pa', 'por', 'un', 'una', 'unos', 'unas', 'que', 'q',
    'cliente', 'empresa', 'nuevo', 'nueva', 'sr', 'sra',
    # formas societarias: no distinguen a nadie
    'sac', 'saa', 'sa', 'srl', 'eirl', 'sociedad', 'anonima', 'cerrada',
}


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


def _raiz(palabra):
    """Singular aproximado: monitores→monitor, cascos→casco, luces→luz no
    hace falta: basta con que la raíz sea subcadena de ambas formas."""
    if len(palabra) > 4 and palabra.endswith('es'):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith('s'):
        return palabra[:-1]
    return palabra


def tokens(texto):
    return [_raiz(p) for p in normalizar(texto).split() if p not in _VACIAS]


def _coincide(token, texto_norm, palabras):
    if token in texto_norm:
        return True
    # un error de tipeo por palabra («logitec», «jbra»): solo tokens no numéricos
    if len(token) >= 4 and not token.isdigit():
        return any(difflib.SequenceMatcher(None, token, p).ratio() >= 0.8 for p in palabras)
    return False


def puntuar(consulta, candidatos):
    """candidatos: [(id, texto, extra)] → [(aciertos, total, id, texto, extra)]."""
    toks = tokens(consulta)
    out = []
    for cid, texto, extra in candidatos:
        norm = normalizar(texto)
        palabras = norm.split()
        aciertos = sum(1 for t in toks if _coincide(t, norm, palabras))
        if aciertos:
            out.append((aciertos, len(toks), cid, texto, extra))
    out.sort(key=lambda x: (-x[0], len(x[3])))
    return out


def resolver(consulta, candidatos):
    """→ (estado, [(id, texto, extra)])."""
    if not tokens(consulta):
        return 'no_encontrado', []
    puntuados = puntuar(consulta, candidatos)
    completos = [p for p in puntuados if p[0] == p[1]]
    if len(completos) == 1:
        _, _, cid, texto, extra = completos[0]
        return 'ok', [(cid, texto, extra)]
    if completos:
        return 'ambiguo', [(c[2], c[3], c[4]) for c in completos[:MAX_OPCIONES]]
    return 'no_encontrado', [(c[2], c[3], c[4]) for c in puntuados[:MAX_OPCIONES]]


# ── fuentes ───────────────────────────────────────────────────────────────────

def candidatos_cliente(empresa):
    from apps.ventas.models import Cliente
    return [
        (cid, f'{nombre} {documento}', {'nombre': nombre, 'documento': documento})
        for cid, nombre, documento in Cliente.objects.filter(empresa=empresa, activo=True)
        .values_list('id', 'nombre', 'documento')
    ]


def candidatos_producto(empresa):
    from apps.inventario.models.producto import Producto
    return [
        (pid, f'{nombre} {sku}', {'nombre': nombre, 'sku': sku})
        for pid, nombre, sku in Producto.objects.filter(empresa=empresa, is_active=True)
        .values_list('id', 'nombre', 'sku')
    ]


def resolver_cliente(empresa, texto):
    return resolver(texto, candidatos_cliente(empresa))


def resolver_producto(empresa, texto):
    return resolver(texto, candidatos_producto(empresa))
