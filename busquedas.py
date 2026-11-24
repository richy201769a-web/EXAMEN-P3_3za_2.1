"""
LIBRERIA PROPIA - METODOS DE BUSQUEDA

    1. Secuencial -> revisa uno por uno. Funciona con datos desordenados.
    2. Binaria    -> divide a la mitad en cada paso. EXIGE datos ordenados.
    3. Hash       -> tabla hash propia (lista de cubetas, encadenamiento).
                     Se construye una vez y cada busqueda revisa una sola
                     cubeta: ideal para busquedas frecuentes.

Como los datasets tienen duplicados, todas regresan TODAS las posiciones
donde aparece el valor (posiciones empezando en 0).
No se usa dict/set de Python para el hash: la tabla es propia.
"""


class ErrorBusqueda(Exception):
    """Error con mensaje listo para mostrar al usuario."""


# ----------------------------------------------------------------------
# 1. BUSQUEDA SECUENCIAL
# ----------------------------------------------------------------------
def busqueda_secuencial(lista, objetivo):
    """Regresa (posiciones, comparaciones). Recorre toda la lista para
    encontrar todas las apariciones."""
    posiciones = []
    comparaciones = 0
    for i in range(len(lista)):
        comparaciones += 1
        if lista[i] == objetivo:
            posiciones.append(i)
    return posiciones, comparaciones


# ----------------------------------------------------------------------
# 2. BUSQUEDA BINARIA (iterativa)
# ----------------------------------------------------------------------
def busqueda_binaria(lista, objetivo, descendente=False):
    """Regresa (posiciones, comparaciones).

    La lista DEBE estar ordenada en el sentido indicado. Primero encuentra
    una aparicion y despues se extiende a izquierda y derecha para incluir
    los duplicados (que en una lista ordenada quedan juntos).
    """
    izq = 0
    der = len(lista) - 1
    comparaciones = 0
    encontrado = -1
    while izq <= der:
        medio = (izq + der) // 2           # sin desbordes ni indices fuera de rango
        comparaciones += 1
        if lista[medio] == objetivo:
            encontrado = medio
            break
        comparaciones += 1
        if descendente:
            ir_derecha = lista[medio] > objetivo
        else:
            ir_derecha = lista[medio] < objetivo
        if ir_derecha:
            izq = medio + 1                # +1: el medio ya se reviso
        else:
            der = medio - 1                # -1: el medio ya se reviso
    if encontrado == -1:
        return [], comparaciones

    inicio = encontrado
    while inicio - 1 >= 0 and lista[inicio - 1] == objetivo:
        comparaciones += 1
        inicio -= 1
    fin = encontrado
    while fin + 1 < len(lista) and lista[fin + 1] == objetivo:
        comparaciones += 1
        fin += 1
    return list(range(inicio, fin + 1)), comparaciones


# ----------------------------------------------------------------------
# 3. BUSQUEDA HASH (tabla propia con encadenamiento)
# ----------------------------------------------------------------------
def _es_primo(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def _siguiente_primo(n):
    while not _es_primo(n):
        n += 1
    return n


def funcion_hash(valor, tamano):
    """Metodo de la division. En Python % siempre da un resultado >= 0
    cuando el divisor es positivo, asi que funciona con negativos."""
    return valor % tamano


def construir_tabla_hash(lista):
    """Crea la tabla: una lista de cubetas; cada cubeta es una lista de
    pares [valor, [posiciones]]. El tamano es un primo cercano a 2n para
    que haya pocas colisiones."""
    tamano = _siguiente_primo(max(11, 2 * len(lista)))
    tabla = [[] for _ in range(tamano)]
    colisiones = 0
    for posicion in range(len(lista)):
        valor = lista[posicion]
        cubeta = tabla[funcion_hash(valor, tamano)]
        agregado = False
        for par in cubeta:
            if par[0] == valor:            # valor repetido: solo se agrega la posicion
                par[1].append(posicion)
                agregado = True
                break
        if not agregado:
            if len(cubeta) > 0:
                colisiones += 1
            cubeta.append([valor, [posicion]])
    return {"tabla": tabla, "tamano": tamano, "colisiones": colisiones, "n": len(lista)}


def busqueda_hash(tabla_hash, objetivo):
    """Regresa (posiciones, comparaciones). Solo revisa UNA cubeta."""
    tabla = tabla_hash["tabla"]
    cubeta = tabla[funcion_hash(objetivo, tabla_hash["tamano"])]
    comparaciones = 0
    for par in cubeta:
        comparaciones += 1
        if par[0] == objetivo:
            return list(par[1]), comparaciones
    return [], comparaciones


NOMBRES = ("Secuencial", "Binaria", "Hash")

COMPLEJIDAD = {
    "Secuencial": "O(n) · no requiere orden",
    "Binaria": "O(log n) · requiere datos ordenados",
    "Hash": "O(1) promedio · requiere construir la tabla (O(n)) una vez",
}
