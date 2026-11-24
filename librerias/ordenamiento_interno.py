"""
LIBRERIA PROPIA - ORDENAMIENTOS INTERNOS (todo en memoria)

Reutiliza los metodos desarrollados en actividades anteriores:
    ADA 1: Burbuja, Insercion, Seleccion
    ADA 2: ShellSort, QuickSort, HeapSort, RadixSort

Se adaptaron para el examen:
    * todos aceptan orden ascendente o descendente,
    * todos regresan (lista_ordenada, estadisticas),
    * todos aceptan una funcion "progreso" opcional para que la interfaz
      muestre el avance y pueda cancelar.

Ninguna funcion modifica la lista original: siempre trabajan sobre una copia.
No se usa .sort(), sorted() ni ninguna biblioteca de ordenamiento.
"""


def _copiar(datos):
    """Copia elemento por elemento (no se modifica la lista original)."""
    copia = []
    for valor in datos:
        copia.append(valor)
    return copia


def _avisar(progreso, hechos, total):
    if progreso is not None:
        progreso(hechos, total)


# ----------------------------------------------------------------------
# ADA 1 - BURBUJA
# Compara vecinos y los intercambia si estan en el orden incorrecto.
# En cada pasada el mayor (o el menor si es descendente) "sube" al final.
# ----------------------------------------------------------------------
def burbuja(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    comparaciones = 0
    intercambios = 0
    n = len(lista)
    for i in range(n - 1):
        hubo_intercambio = False
        # Los ultimos i elementos ya quedaron en su lugar
        for j in range(n - 1 - i):
            comparaciones += 1
            if descendente:
                desordenados = lista[j] < lista[j + 1]
            else:
                desordenados = lista[j] > lista[j + 1]
            if desordenados:
                lista[j], lista[j + 1] = lista[j + 1], lista[j]
                intercambios += 1
                hubo_intercambio = True
        _avisar(progreso, i + 1, n - 1)
        # Si no hubo intercambios la lista ya esta ordenada
        if not hubo_intercambio:
            break
    return lista, {"comparaciones": comparaciones, "movimientos": intercambios}


# ----------------------------------------------------------------------
# ADA 1 - INSERCION
# Toma cada elemento y lo inserta en su lugar dentro de la parte ya
# ordenada, recorriendo a la derecha los que deben ir despues.
# ----------------------------------------------------------------------
def insercion(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    comparaciones = 0
    desplazamientos = 0
    n = len(lista)
    for i in range(1, n):
        actual = lista[i]
        j = i - 1
        while j >= 0:
            comparaciones += 1
            if descendente:
                va_despues = lista[j] < actual
            else:
                va_despues = lista[j] > actual
            if not va_despues:
                break
            lista[j + 1] = lista[j]
            desplazamientos += 1
            j -= 1
        lista[j + 1] = actual
        _avisar(progreso, i, n - 1)
    return lista, {"comparaciones": comparaciones, "movimientos": desplazamientos}


# ----------------------------------------------------------------------
# ADA 1 - SELECCION
# Busca el menor (o el mayor) de la parte sin ordenar y lo coloca al inicio.
# ----------------------------------------------------------------------
def seleccion(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    comparaciones = 0
    intercambios = 0
    n = len(lista)
    for i in range(n - 1):
        elegido = i
        for j in range(i + 1, n):
            comparaciones += 1
            if descendente:
                es_mejor = lista[j] > lista[elegido]
            else:
                es_mejor = lista[j] < lista[elegido]
            if es_mejor:
                elegido = j
        if elegido != i:
            lista[i], lista[elegido] = lista[elegido], lista[i]
            intercambios += 1
        _avisar(progreso, i + 1, n - 1)
    return lista, {"comparaciones": comparaciones, "movimientos": intercambios}


# ----------------------------------------------------------------------
# ADA 2 - SHELLSORT
# Insercion con "saltos" que se van reduciendo (secuencia de Knuth
# 1, 4, 13, 40, ...). Al final el salto es 1 = insercion normal, pero la
# lista ya esta casi ordenada y se hace muy rapido.
# ----------------------------------------------------------------------
def shell_sort(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    comparaciones = 0
    movimientos = 0
    n = len(lista)

    salto = 1
    while salto < n // 3:
        salto = 3 * salto + 1

    total_saltos = 0
    s = salto
    while s >= 1:
        total_saltos += 1
        s //= 3

    hechos = 0
    while salto >= 1:
        for i in range(salto, n):
            actual = lista[i]
            j = i
            while j >= salto:
                comparaciones += 1
                if descendente:
                    mover = lista[j - salto] < actual
                else:
                    mover = lista[j - salto] > actual
                if not mover:
                    break
                lista[j] = lista[j - salto]
                movimientos += 1
                j -= salto
            lista[j] = actual
        salto //= 3
        hechos += 1
        _avisar(progreso, hechos, total_saltos)
    return lista, {"comparaciones": comparaciones, "movimientos": movimientos}


# ----------------------------------------------------------------------
# ADA 2 - QUICKSORT
# Elige un pivote (mediana de tres), separa la lista en
#     | van antes del pivote | iguales al pivote | van despues |
# y repite con cada lado. Usa una pila propia (lista de pares) en lugar de
# recursion, asi nunca se llega al limite de recursion de Python.
# Agrupar los iguales evita que se degrade con muchos duplicados.
# ----------------------------------------------------------------------
def _mediana_de_tres(lista, izq, der):
    """Coloca en lista[der] la mediana de (primero, medio, ultimo)."""
    medio = (izq + der) // 2
    if lista[medio] < lista[izq]:
        lista[medio], lista[izq] = lista[izq], lista[medio]
    if lista[der] < lista[izq]:
        lista[der], lista[izq] = lista[izq], lista[der]
    if lista[der] < lista[medio]:
        lista[der], lista[medio] = lista[medio], lista[der]
    lista[medio], lista[der] = lista[der], lista[medio]


def _particionar(lista, izq, der, descendente, est):
    _mediana_de_tres(lista, izq, der)
    pivote = lista[der]
    menor, i, mayor = izq, izq, der
    while i <= mayor:
        est["comparaciones"] += 1
        if descendente:
            va_antes = lista[i] > pivote
            va_despues = lista[i] < pivote
        else:
            va_antes = lista[i] < pivote
            va_despues = lista[i] > pivote
        if va_antes:
            lista[menor], lista[i] = lista[i], lista[menor]
            est["movimientos"] += 1
            menor += 1
            i += 1
        elif va_despues:
            lista[i], lista[mayor] = lista[mayor], lista[i]
            est["movimientos"] += 1
            mayor -= 1
        else:
            i += 1
    return menor, mayor


def quick_sort(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    est = {"comparaciones": 0, "movimientos": 0}
    n = len(lista)
    pila = [(0, n - 1)]
    colocados = 0
    while len(pila) > 0:
        izq, der = pila.pop()
        if izq >= der:
            if izq == der:
                colocados += 1
            continue
        inicio, fin = _particionar(lista, izq, der, descendente, est)
        colocados += fin - inicio + 1          # los iguales al pivote ya quedaron
        pila.append((izq, inicio - 1))
        pila.append((fin + 1, der))
        _avisar(progreso, colocados, n)
    return lista, est


# ----------------------------------------------------------------------
# ADA 2 - HEAPSORT
# Convierte la lista en un monticulo (arbol guardado en la misma lista):
# para ascendente un monticulo de maximos, para descendente uno de minimos.
# Luego manda la raiz al final y repara el monticulo, una y otra vez.
# ----------------------------------------------------------------------
def _hundir(lista, raiz, fin, descendente, est):
    while True:
        hijo = 2 * raiz + 1                     # hijo izquierdo
        if hijo >= fin:
            return
        if hijo + 1 < fin:
            est["comparaciones"] += 1
            if descendente:
                derecho_gana = lista[hijo + 1] < lista[hijo]
            else:
                derecho_gana = lista[hijo + 1] > lista[hijo]
            if derecho_gana:
                hijo += 1
        est["comparaciones"] += 1
        if descendente:
            ya_esta = lista[raiz] <= lista[hijo]
        else:
            ya_esta = lista[raiz] >= lista[hijo]
        if ya_esta:
            return
        lista[raiz], lista[hijo] = lista[hijo], lista[raiz]
        est["movimientos"] += 1
        raiz = hijo


def heap_sort(datos, descendente=False, progreso=None):
    lista = _copiar(datos)
    est = {"comparaciones": 0, "movimientos": 0}
    n = len(lista)
    # 1) Construir el monticulo
    for i in range(n // 2 - 1, -1, -1):
        _hundir(lista, i, n, descendente, est)
    # 2) Mandar la raiz al final y reparar el resto
    hechos = 0
    for fin in range(n - 1, 0, -1):
        lista[0], lista[fin] = lista[fin], lista[0]
        est["movimientos"] += 1
        _hundir(lista, 0, fin, descendente, est)
        hechos += 1
        if hechos % 256 == 0:
            _avisar(progreso, hechos, n - 1)
    _avisar(progreso, n - 1, n - 1)
    return lista, est


# ----------------------------------------------------------------------
# ADA 2 - RADIXSORT (LSD, base 10)
# No compara: reparte los numeros en 10 cubetas segun el digito de las
# unidades, luego decenas, centenas... Los negativos se ordenan aparte por
# su valor absoluto y se colocan invertidos antes de los positivos.
# ----------------------------------------------------------------------
def _mayor(lista):
    mayor = lista[0]
    for valor in lista:
        if valor > mayor:
            mayor = valor
    return mayor


def _invertir(lista):
    invertida = []
    for i in range(len(lista) - 1, -1, -1):
        invertida.append(lista[i])
    return invertida


def _radix_no_negativos(lista, est):
    if len(lista) == 0:
        return lista
    mayor = _mayor(lista)
    exp = 1                                     # 1 = unidades, 10 = decenas, ...
    while mayor // exp > 0:
        cubetas = [[] for _ in range(10)]
        for numero in lista:
            cubetas[(numero // exp) % 10].append(numero)
            est["movimientos"] += 1
        lista = []
        for cubeta in cubetas:
            for numero in cubeta:
                lista.append(numero)
        exp *= 10
    return lista


def radix_sort(datos, descendente=False, progreso=None):
    est = {"comparaciones": 0, "movimientos": 0}
    negativos = []
    no_negativos = []
    for valor in datos:
        if valor < 0:
            negativos.append(-valor)
        else:
            no_negativos.append(valor)
    _avisar(progreso, 1, 3)
    negativos = _radix_no_negativos(negativos, est)
    negativos = [-v for v in _invertir(negativos)]
    _avisar(progreso, 2, 3)
    no_negativos = _radix_no_negativos(no_negativos, est)
    lista = negativos + no_negativos
    if descendente:
        lista = _invertir(lista)
    _avisar(progreso, 3, 3)
    return lista, est


# ----------------------------------------------------------------------
# Catalogo usado por la interfaz
# ----------------------------------------------------------------------
ALGORITMOS_INTERNOS = {
    "Burbuja": burbuja,
    "Inserción": insercion,
    "Selección": seleccion,
    "ShellSort": shell_sort,
    "QuickSort": quick_sort,
    "HeapSort": heap_sort,
    "RadixSort": radix_sort,
}

# Metodos O(n^2): se avisa al usuario antes de usarlos con muchos datos
CUADRATICOS = ("Burbuja", "Inserción", "Selección")

COMPLEJIDAD = {
    "Burbuja": "O(n²)",
    "Inserción": "O(n²)  ·  O(n) si ya está casi ordenado",
    "Selección": "O(n²) siempre",
    "ShellSort": "≈ O(n^1.5) con secuencia de Knuth",
    "QuickSort": "O(n log n) promedio",
    "HeapSort": "O(n log n) siempre",
    "RadixSort": "O(d·n), d = número de dígitos",
}


def esta_ordenada(lista, descendente=False):
    """True si la lista esta en el orden pedido (se usa para verificar)."""
    for i in range(len(lista) - 1):
        if descendente:
            if lista[i] < lista[i + 1]:
                return False
        else:
            if lista[i] > lista[i + 1]:
                return False
    return True
