"""
LIBRERIA PROPIA - ORDENAMIENTOS EXTERNOS (trabajan sobre archivos)

Reutiliza los metodos de la ADA "Metodos de Ordenamiento 2 (externos)":
    1. Intercalacion       -> une dos archivos YA ordenados en uno solo.
    2. Mezcla Directa      -> particiones de tamano fijo 1, 2, 4, 8, ...
    3. Mezcla Equilibrada  -> particiones naturales (tramos ya ordenados).

Formato de los archivos de trabajo: un numero entero por linea.
Los datos NUNCA se cargan completos en memoria durante el ordenamiento:
se leen y escriben linea por linea, que es la idea de un ordenamiento
externo (archivos mas grandes que la memoria).

Solo usa "os" (permitido por el examen). No usa .sort() ni sorted().
"""

import os


class ErrorOrdenExterno(Exception):
    """Error con mensaje listo para mostrar al usuario."""


# ----------------------------------------------------------------------
# Utilidades de archivo (un numero por linea)
# ----------------------------------------------------------------------
def _leer(f):
    """Lee el siguiente entero del archivo o None si ya no hay mas."""
    linea = f.readline()
    while linea and not linea.strip():
        linea = f.readline()
    if not linea:
        return None
    return int(linea)


def _escribir(f, valor, est):
    f.write(str(valor) + "\n")
    est["movimientos"] += 1


def _va_antes(x, y, descendente):
    """True si x puede ir antes que y respetando el orden."""
    if descendente:
        return x >= y
    return x <= y


def escribir_lista(ruta, lista):
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        for valor in lista:
            f.write(str(valor) + "\n")


def leer_lista(ruta):
    lista = []
    with open(ruta, "r", encoding="utf-8") as f:
        valor = _leer(f)
        while valor is not None:
            lista.append(valor)
            valor = _leer(f)
    return lista


def _contar(ruta):
    n = 0
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                n += 1
    return n


def _borrar(ruta):
    try:
        if os.path.isfile(ruta):
            os.remove(ruta)
    except OSError:
        pass


def _nuevas_estadisticas():
    return {"comparaciones": 0, "movimientos": 0, "pasadas": 0, "procesados": 0}


def _tick(est, progreso, total):
    """Cuenta un registro procesado y avisa a la interfaz cada 2048."""
    est["procesados"] += 1
    if progreso is not None and est["procesados"] % 2048 == 0:
        progreso(min(est["procesados"], total), total)


# ----------------------------------------------------------------------
# 1. INTERCALACION
# Une A y B (ambos ordenados) en C comparando el primero de cada archivo
# y copiando el que debe ir antes. Si uno se acaba, se copia el resto
# del otro. Tambien verifica que A y B realmente esten ordenados.
# ----------------------------------------------------------------------
def intercalar_archivos(ruta_a, ruta_b, ruta_salida, descendente=False):
    est = _nuevas_estadisticas()
    with open(ruta_a, "r", encoding="utf-8") as fa, \
            open(ruta_b, "r", encoding="utf-8") as fb, \
            open(ruta_salida, "w", encoding="utf-8", newline="\n") as fc:
        a = _leer(fa)
        b = _leer(fb)
        previo_a = previo_b = None
        pos_a = pos_b = 1

        def revisar(previo, actual, nombre, pos):
            if previo is not None and actual is not None and not _va_antes(previo, actual, descendente):
                orden = "descendente" if descendente else "ascendente"
                raise ErrorOrdenExterno(
                    f"El archivo {nombre} no está ordenado en forma {orden} "
                    f"(dato #{pos}: {actual} después de {previo}). "
                    "La intercalación solo funciona con archivos ya ordenados.")

        while a is not None and b is not None:
            est["comparaciones"] += 1
            if _va_antes(a, b, descendente):        # empate: primero A (estable)
                _escribir(fc, a, est)
                previo_a, a = a, _leer(fa)
                pos_a += 1
                revisar(previo_a, a, "A", pos_a)
            else:
                _escribir(fc, b, est)
                previo_b, b = b, _leer(fb)
                pos_b += 1
                revisar(previo_b, b, "B", pos_b)
        while a is not None:                        # B se acabo: resto de A
            _escribir(fc, a, est)
            previo_a, a = a, _leer(fa)
            pos_a += 1
            revisar(previo_a, a, "A", pos_a)
        while b is not None:                        # A se acabo: resto de B
            _escribir(fc, b, est)
            previo_b, b = b, _leer(fb)
            pos_b += 1
            revisar(previo_b, b, "B", pos_b)
    est["pasadas"] = 1
    return est


# ----------------------------------------------------------------------
# 2. MEZCLA DIRECTA
# Repite con tam = 1, 2, 4, 8 ... mientras tam < n:
#   PARTICION: copia bloques de "tam" datos de F alternando en F1 y F2.
#   FUSION:    intercala un bloque de F1 con uno de F2 y lo escribe en F.
# Despues de cada pasada los bloques ordenados miden el doble.
# ----------------------------------------------------------------------
def _particionar_bloques(ruta_f, ruta_f1, ruta_f2, tam, est, progreso, total):
    with open(ruta_f, "r", encoding="utf-8") as f, \
            open(ruta_f1, "w", encoding="utf-8", newline="\n") as f1, \
            open(ruta_f2, "w", encoding="utf-8", newline="\n") as f2:
        salidas = (f1, f2)
        destino = 0
        cuenta = 0
        valor = _leer(f)
        while valor is not None:
            _escribir(salidas[destino], valor, est)
            cuenta += 1
            if cuenta == tam:                   # bloque completo: cambiar de archivo
                cuenta = 0
                destino = 1 - destino
            _tick(est, progreso, total)
            valor = _leer(f)


def _fusionar_bloques(ruta_f1, ruta_f2, ruta_f, tam, descendente, est, progreso, total):
    with open(ruta_f1, "r", encoding="utf-8") as f1, \
            open(ruta_f2, "r", encoding="utf-8") as f2, \
            open(ruta_f, "w", encoding="utf-8", newline="\n") as f:
        a = _leer(f1)
        b = _leer(f2)
        while a is not None or b is not None:
            usados_a = 0
            usados_b = 0
            while usados_a < tam and usados_b < tam and a is not None and b is not None:
                est["comparaciones"] += 1
                if _va_antes(a, b, descendente):
                    _escribir(f, a, est)
                    a = _leer(f1)
                    usados_a += 1
                else:
                    _escribir(f, b, est)
                    b = _leer(f2)
                    usados_b += 1
                _tick(est, progreso, total)
            while usados_a < tam and a is not None:     # resto del bloque de F1
                _escribir(f, a, est)
                a = _leer(f1)
                usados_a += 1
                _tick(est, progreso, total)
            while usados_b < tam and b is not None:     # resto del bloque de F2
                _escribir(f, b, est)
                b = _leer(f2)
                usados_b += 1
                _tick(est, progreso, total)


def mezcla_directa(ruta_f, carpeta, descendente=False, progreso=None):
    """Ordena el archivo F en su lugar. Regresa las estadisticas."""
    est = _nuevas_estadisticas()
    n = _contar(ruta_f)
    ruta_f1 = os.path.join(carpeta, "F1.txt")
    ruta_f2 = os.path.join(carpeta, "F2.txt")
    total_pasadas = (n - 1).bit_length() if n > 1 else 0     # techo(log2 n)
    total = max(1, total_pasadas * 2 * n)
    try:
        tam = 1
        while tam < n:
            est["pasadas"] += 1
            _particionar_bloques(ruta_f, ruta_f1, ruta_f2, tam, est, progreso, total)
            _fusionar_bloques(ruta_f1, ruta_f2, ruta_f, tam, descendente, est, progreso, total)
            tam *= 2
    finally:
        _borrar(ruta_f1)
        _borrar(ruta_f2)
    if progreso is not None:
        progreso(total, total)
    return est


# ----------------------------------------------------------------------
# 3. MEZCLA EQUILIBRADA (mezcla natural con 4 archivos)
#   Particion inicial: reparte los TRAMOS (secuencias que ya vienen
#   ordenadas) de F alternando en F2 y F3.
#   Pasadas: fusiona un tramo de cada archivo de entrada y escribe los
#   resultados alternando en dos archivos de salida; luego se invierten
#   los papeles. Termina cuando solo queda un tramo.
# Aprovecha el orden que ya traen los datos: si estan casi ordenados
# termina en muy pocas pasadas.
# ----------------------------------------------------------------------
def _copiar_tramo(f, valor, salida, descendente, est, progreso, total):
    """Copia el tramo que empieza en 'valor'. Regresa el inicio del siguiente tramo."""
    while True:
        _escribir(salida, valor, est)
        _tick(est, progreso, total)
        siguiente = _leer(f)
        if siguiente is None:
            return None
        est["comparaciones"] += 1
        if not _va_antes(valor, siguiente, descendente):     # se rompio el orden: fin del tramo
            return siguiente
        valor = siguiente


def _fusionar_tramo(fa, a, fb, b, salida, descendente, est, progreso, total):
    """Intercala el tramo actual de A con el tramo actual de B."""
    fin_a = False
    fin_b = False
    while not fin_a and not fin_b:
        est["comparaciones"] += 1
        if _va_antes(a, b, descendente):
            _escribir(salida, a, est)
            siguiente = _leer(fa)
            if siguiente is None or not _va_antes(a, siguiente, descendente):
                fin_a = True
            a = siguiente
        else:
            _escribir(salida, b, est)
            siguiente = _leer(fb)
            if siguiente is None or not _va_antes(b, siguiente, descendente):
                fin_b = True
            b = siguiente
        _tick(est, progreso, total)
    if not fin_a:
        a = _copiar_tramo(fa, a, salida, descendente, est, progreso, total)
    if not fin_b:
        b = _copiar_tramo(fb, b, salida, descendente, est, progreso, total)
    return a, b


def _particion_inicial(ruta_f, ruta_f2, ruta_f3, descendente, est, progreso, total):
    tramos = 0
    with open(ruta_f, "r", encoding="utf-8") as f, \
            open(ruta_f2, "w", encoding="utf-8", newline="\n") as f2, \
            open(ruta_f3, "w", encoding="utf-8", newline="\n") as f3:
        salidas = (f2, f3)
        actual = 0
        valor = _leer(f)
        while valor is not None:
            tramos += 1
            valor = _copiar_tramo(f, valor, salidas[actual], descendente, est, progreso, total)
            actual = 1 - actual
    return tramos


def _particion_fusion(ruta_a, ruta_b, ruta_c, ruta_d, descendente, est, progreso, total):
    tramos = 0
    with open(ruta_a, "r", encoding="utf-8") as fa, \
            open(ruta_b, "r", encoding="utf-8") as fb, \
            open(ruta_c, "w", encoding="utf-8", newline="\n") as fc, \
            open(ruta_d, "w", encoding="utf-8", newline="\n") as fd:
        salidas = (fc, fd)
        actual = 0
        a = _leer(fa)
        b = _leer(fb)
        while a is not None or b is not None:
            salida = salidas[actual]
            tramos += 1
            if a is not None and b is not None:
                a, b = _fusionar_tramo(fa, a, fb, b, salida, descendente, est, progreso, total)
            elif a is not None:
                a = _copiar_tramo(fa, a, salida, descendente, est, progreso, total)
            else:
                b = _copiar_tramo(fb, b, salida, descendente, est, progreso, total)
            actual = 1 - actual
    return tramos


def mezcla_equilibrada(ruta_f, carpeta, descendente=False, progreso=None):
    """Ordena el archivo F (el resultado queda en F). Regresa las estadisticas."""
    est = _nuevas_estadisticas()
    n = _contar(ruta_f)
    rutas = {
        "F": ruta_f,
        "F1": os.path.join(carpeta, "F1.txt"),
        "F2": os.path.join(carpeta, "F2.txt"),
        "F3": os.path.join(carpeta, "F3.txt"),
    }
    total = max(1, n * 2 * max(1, n.bit_length()))
    try:
        tramos = _particion_inicial(rutas["F"], rutas["F2"], rutas["F3"], descendente, est, progreso, total)
        est["tramos_iniciales"] = tramos
        origen = ("F2", "F3")
        destino = ("F", "F1")
        while tramos > 1:
            est["pasadas"] += 1
            tramos = _particion_fusion(rutas[origen[0]], rutas[origen[1]],
                                       rutas[destino[0]], rutas[destino[1]],
                                       descendente, est, progreso, total)
            origen, destino = destino, origen
        # El resultado quedo en origen[0]; si no es F se copia a F
        if n > 0 and origen[0] != "F":
            with open(rutas[origen[0]], "r", encoding="utf-8") as fuente, \
                    open(rutas["F"], "w", encoding="utf-8", newline="\n") as f:
                valor = _leer(fuente)
                while valor is not None:
                    f.write(str(valor) + "\n")
                    valor = _leer(fuente)
    finally:
        _borrar(rutas["F1"])
        _borrar(rutas["F2"])
        _borrar(rutas["F3"])
    if progreso is not None:
        progreso(total, total)
    return est


# ----------------------------------------------------------------------
# Catalogo y funcion de alto nivel usada por la interfaz
# ----------------------------------------------------------------------
ALGORITMOS_EXTERNOS = {
    "Mezcla Directa": mezcla_directa,
    "Mezcla Equilibrada": mezcla_equilibrada,
}

COMPLEJIDAD = {
    "Mezcla Directa": "O(n log n) · ⌈log₂ n⌉ pasadas sobre disco",
    "Mezcla Equilibrada": "O(n log t) · t = tramos naturales iniciales",
    "Intercalación": "O(n + m) · une 2 archivos ordenados",
}


def ordenar_externo(datos, nombre, carpeta, descendente=False, progreso=None):
    """Escribe los datos en un archivo F, lo ordena con el metodo externo
    elegido y regresa (lista_ordenada, estadisticas).
    Los archivos temporales (F, F1, F2, F3) se borran al terminar,
    incluso si ocurre un error o el usuario cancela.
    """
    if nombre not in ALGORITMOS_EXTERNOS:
        raise ErrorOrdenExterno(f"Método externo desconocido: {nombre}")
    os.makedirs(carpeta, exist_ok=True)
    ruta_f = os.path.join(carpeta, "F.txt")
    try:
        escribir_lista(ruta_f, datos)
        est = ALGORITMOS_EXTERNOS[nombre](ruta_f, carpeta, descendente, progreso)
        lista = leer_lista(ruta_f)
    finally:
        _borrar(ruta_f)
    return lista, est
