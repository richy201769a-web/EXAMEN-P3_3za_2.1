"""
LIBRERIA PROPIA - LABORATORIO DE RENDIMIENTO

Comprueba con MEDICIONES REALES lo que pide el requerimiento 6 (comparacion
basica) en lugar de solo afirmarlo:

  1. Escalabilidad: mide cada algoritmo con tamanos crecientes (250, 500,
     1000, 2000, 5000, ...) y calcula el EXPONENTE DE CRECIMIENTO b del
     tiempo (t ~ n^b) con minimos cuadrados sobre log(n) y log(t):
         b ~ 2   -> crece como n^2      (Burbuja, Insercion, Seleccion)
         b ~ 1.1 -> crece como n log n  (QuickSort, HeapSort)
         b ~ 1   -> crece lineal        (RadixSort)
  2. Escenarios del requerimiento 6: datos pequenos, masivos, casi ordenados,
     orden inverso y muchos duplicados -> se mide el ganador de cada uno.
  3. Busquedas frecuentes: costo total de 1,000 busquedas con cada metodo
     (incluye la preparacion: ordenar una vez para la binaria, construir la
     tabla para la hash).
  4. Recomendacion empirica: el ganador medido de cada escenario.

Solo usa las librerias propias y "time" (permitido). Los datos de prueba se
generan con un generador congruencial lineal PROPIO (no usa random) y el
logaritmo se calcula con una serie propia (no usa math).
"""

import time

from librerias import ordenamiento_interno as oi
from librerias import ordenamiento_externo as oe
from librerias import busquedas as bq

LN2 = 0.6931471805599453
TAMANOS = (250, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000)
PRESUPUESTO = 1.5          # segundos: si una medicion tarda mas, ya no se prueba un n mayor
MAX_CUADRATICO = 5000      # en los escenarios, O(n^2) solo se mide hasta este tamano...
ADAPTATIVOS = ("Burbuja", "Inserción")   # ...salvo estos con datos casi ordenados, donde son casi O(n)


class Cancelado(Exception):
    pass


# ----------------------------------------------------------------------
# Matematicas propias
# ----------------------------------------------------------------------
def ln(x):
    """Logaritmo natural sin la libreria math.
    x = m * 2^k con m en [1, 2):  ln(x) = k*ln(2) + 2*atanh((m-1)/(m+1))."""
    if x <= 0:
        raise ValueError("ln solo existe para x > 0")
    k = 0
    while x >= 2:
        x /= 2
        k += 1
    while x < 1:
        x *= 2
        k -= 1
    y = (x - 1) / (x + 1)
    y2 = y * y
    termino = y
    suma = 0.0
    i = 1
    while abs(termino) > 1e-17:
        suma += termino / i
        termino *= y2
        i += 2
    return 2 * suma + k * LN2


def exponente_crecimiento(puntos, ultimos=3):
    """Pendiente de la recta de minimos cuadrados de log(t) contra log(n),
    usando los 'ultimos' tamanos (los mas grandes: ahi se ve el crecimiento
    real, sin el ruido de los costos fijos). Ignora tiempos < 0.05 ms."""
    xs = []
    ys = []
    for n, seg in puntos[-ultimos:]:
        if n > 0 and seg >= 0.00005:
            xs.append(ln(n))
            ys.append(ln(seg))
    if len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = 0.0
    den = 0.0
    for x, y in zip(xs, ys):
        num += (x - mx) * (y - my)
        den += (x - mx) * (x - mx)
    if den == 0:
        return None
    return num / den


def interpretar_exponente(b):
    """Con tamanos de cientos a miles, n y n log n dan exponentes muy parecidos
    (1.0 contra ~1.1) y el ruido de medicion no permite separarlos con certeza;
    por eso se reportan juntos. La diferencia clara es contra n^2 (b ~ 2)."""
    if b is None:
        return "Sin datos suficientes"
    if b < 0.95:
        return "≈ lineal  (n)"
    if b < 1.3:
        return "≈ n log n  o  lineal"
    if b < 1.75:
        return "≈ n^1.5"
    return "≈ cuadrático  (n²)"


def generador(semilla=2026):
    """Generador congruencial lineal propio: siguiente(limite) -> entero en [0, limite)."""
    estado = [semilla % 2147483648]

    def siguiente(limite):
        estado[0] = (1103515245 * estado[0] + 12345) % 2147483648
        return estado[0] % limite
    return siguiente


# ----------------------------------------------------------------------
# Medicion
# ----------------------------------------------------------------------
def ordenadores(nombres, carpeta):
    """Regresa {nombre: (tipo, funcion(datos, progreso) -> (lista, est))}."""
    resultado = {}
    for nombre in nombres:
        if nombre in oi.ALGORITMOS_INTERNOS:
            f = oi.ALGORITMOS_INTERNOS[nombre]
            resultado[nombre] = ("Interno", lambda d, p, f=f: f(d, False, p))
        elif nombre in oe.ALGORITMOS_EXTERNOS:
            resultado[nombre] = ("Externo",
                                 lambda d, p, n=nombre: oe.ordenar_externo(d, n, carpeta, False, p))
    return resultado


def medir(funcion, datos, progreso=None, pausa=None, repeticiones=1):
    """Mejor tiempo de 'repeticiones' corridas. 'pausa()' regresa el tiempo
    acumulado que la interfaz uso para refrescarse (se descuenta)."""
    mejor = None
    for _ in range(repeticiones):
        p0 = pausa() if pausa else 0.0
        inicio = time.perf_counter()
        lista, _est = funcion(datos, progreso)
        seg = time.perf_counter() - inicio - ((pausa() - p0) if pausa else 0.0)
        if not oi.esta_ordenada(lista):
            raise RuntimeError("Un algoritmo no ordenó correctamente durante el laboratorio")
        if mejor is None or seg < mejor:
            mejor = seg
        if seg > 0.25:                 # una medicion larga ya es estable: no hace falta repetirla
            break
    return max(mejor, 0.0)


def _repeticiones(n):
    """Se toma el MEJOR tiempo de varias corridas para quitar ruido del sistema."""
    if n <= 100:
        return 40
    if n <= 2000:
        return 5
    if n <= 20000:
        return 3
    return 1


# ----------------------------------------------------------------------
# 1. Escalabilidad
# ----------------------------------------------------------------------
def escalabilidad(datos, nombres, carpeta, progreso=None, pausa=None, aviso=None):
    """Para cada algoritmo mide tamanos crecientes (prefijos de los datos)
    hasta que una medicion supera el presupuesto de tiempo."""
    n_total = len(datos)
    tamanos = [t for t in TAMANOS if t < n_total] + [n_total]
    funciones = ordenadores(nombres, carpeta)
    series = []
    for nombre in nombres:
        tipo, f = funciones[nombre]
        puntos = []
        for n in tamanos:
            if aviso:
                aviso(f"Escalabilidad · {nombre} con {n:,} datos")
            seg = medir(f, datos[:n], progreso, pausa, _repeticiones(n))
            puntos.append((n, seg))
            if seg > PRESUPUESTO:
                break
        b = exponente_crecimiento(puntos)
        interpretacion = interpretar_exponente(b)
        if tipo == "Externo" and b is not None and b < 1.0:
            interpretacion += " · domina el costo fijo del disco"
        series.append({"algoritmo": nombre, "tipo": tipo, "puntos": puntos, "exponente": b,
                       "interpretacion": interpretacion,
                       "teorica": oi.COMPLEJIDAD.get(nombre) or oe.COMPLEJIDAD.get(nombre, "")})
    return series


# ----------------------------------------------------------------------
# 2. Escenarios del requerimiento 6
# ----------------------------------------------------------------------
def generar_escenarios(datos, semilla=2026):
    """Crea los escenarios a partir de los datos cargados (todos se ordenan
    de forma ascendente)."""
    azar = generador(semilla)
    ordenados, _ = oi.quick_sort(datos)
    casi = list(ordenados)
    # 5 % de los elementos se mueven a lo mas 10 posiciones: cada dato queda CERCA de su lugar
    for _ in range(max(1, len(casi) // 20)):
        if len(casi) < 2:
            break
        i = azar(len(casi) - 1)
        j = i + 1 + azar(10)
        if j >= len(casi):
            j = len(casi) - 1
        casi[i], casi[j] = casi[j], casi[i]
    inverso, _ = oi.quick_sort(datos, descendente=True)
    duplicados = [v % 50 for v in datos]
    return [
        ("Datos pequeños", f"primeros {min(30, len(datos))} datos", datos[:30]),
        ("Datos masivos", f"{len(datos):,} datos aleatorios", datos),
        ("Datos parcialmente ordenados", "5 % de los datos a lo más 10 lugares de su posición", casi),
        ("Orden inverso", "de mayor a menor (peor caso de varios métodos)", inverso),
        ("Muchos duplicados", "solo 50 valores distintos", duplicados),
    ]


def matriz_escenarios(datos, nombres, carpeta, progreso=None, pausa=None, aviso=None):
    """Mide cada algoritmo en cada escenario. Regresa (escenarios, matriz)
    donde matriz[i][j] = segundos o None si se omitio (O(n^2) muy grande)."""
    escenarios = generar_escenarios(datos)
    funciones = ordenadores(nombres, carpeta)
    matriz = []
    for titulo, _desc, valores in escenarios:
        fila = []
        casi_ordenado = titulo == "Datos parcialmente ordenados"
        for nombre in nombres:
            excepcion = casi_ordenado and nombre in ADAPTATIVOS
            if nombre in oi.CUADRATICOS and len(valores) > MAX_CUADRATICO and not excepcion:
                fila.append(None)
                continue
            if aviso:
                aviso(f"Escenario «{titulo}» · {nombre}")
            fila.append(medir(funciones[nombre][1], valores, progreso, pausa, _repeticiones(len(valores))))
        matriz.append(fila)
    return [(t, d, len(v)) for t, d, v in escenarios], matriz


# ----------------------------------------------------------------------
# 3. Busquedas frecuentes
# ----------------------------------------------------------------------
def busquedas_frecuentes(datos, k=1000, muestra=200, aviso=None):
    """Costo total proyectado de k busquedas (se mide una muestra y se
    proyecta). Incluye la preparacion de cada metodo."""
    azar = generador(7)
    objetivos = []
    for i in range(muestra):
        if i % 2 == 0:
            objetivos.append(datos[azar(len(datos))])          # valor que si existe
        else:
            objetivos.append(-1 - azar(1000))                  # valor que no existe

    if aviso:
        aviso("Búsquedas frecuentes · secuencial")
    inicio = time.perf_counter()
    for obj in objetivos:
        bq.busqueda_secuencial(datos, obj)
    por_busqueda_sec = (time.perf_counter() - inicio) / muestra

    if aviso:
        aviso("Búsquedas frecuentes · binaria")
    inicio = time.perf_counter()
    ordenados, _ = oi.quick_sort(datos)
    prep_bin = time.perf_counter() - inicio
    inicio = time.perf_counter()
    for obj in objetivos:
        bq.busqueda_binaria(ordenados, obj)
    por_busqueda_bin = (time.perf_counter() - inicio) / muestra

    if aviso:
        aviso("Búsquedas frecuentes · hash")
    inicio = time.perf_counter()
    tabla = bq.construir_tabla_hash(datos)
    prep_hash = time.perf_counter() - inicio
    inicio = time.perf_counter()
    for obj in objetivos:
        bq.busqueda_hash(tabla, obj)
    por_busqueda_hash = (time.perf_counter() - inicio) / muestra

    return [
        {"metodo": "Secuencial", "preparacion": 0.0, "por_busqueda": por_busqueda_sec,
         "total": por_busqueda_sec * k, "nota": "sin preparación"},
        {"metodo": "Binaria", "preparacion": prep_bin, "por_busqueda": por_busqueda_bin,
         "total": prep_bin + por_busqueda_bin * k, "nota": "incluye ordenar una vez (QuickSort)"},
        {"metodo": "Hash", "preparacion": prep_hash, "por_busqueda": por_busqueda_hash,
         "total": prep_hash + por_busqueda_hash * k, "nota": "incluye construir la tabla"},
    ]


# ----------------------------------------------------------------------
# 4. Recomendacion empirica
# ----------------------------------------------------------------------
def _ganador(nombres, tiempos, permitidos=None):
    mejor = None
    for nombre, t in zip(nombres, tiempos):
        if t is None or (permitidos and nombre not in permitidos):
            continue
        if mejor is None or t < mejor[1]:
            mejor = (nombre, t)
    return mejor


def recomendacion_empirica(nombres, escenarios, matriz, busquedas, teoricas):
    """Compara el ganador medido de cada escenario con la recomendacion
    teorica (teoricas: {escenario: texto_recomendado})."""
    indice = {t: i for i, (t, _d, _n) in enumerate(escenarios)}
    filas = []

    def agregar(escenario, ganador, detalle):
        teorica = teoricas.get(escenario, "")
        coincide = ganador is not None and ganador in teorica
        filas.append({"escenario": escenario, "ganador": ganador or "—", "detalle": detalle,
                      "teorica": teorica, "coincide": coincide})

    for escenario in ("Datos pequeños", "Datos masivos", "Datos parcialmente ordenados"):
        g = _ganador(nombres, matriz[indice[escenario]])
        agregar(escenario, g[0] if g else None, _tiempo(g[1]) if g else "")
    externos = [n for n in nombres if n in oe.ALGORITMOS_EXTERNOS]
    g = _ganador(nombres, matriz[indice["Datos masivos"]], externos)
    agregar("Archivos externos", g[0] if g else None, (_tiempo(g[1]) + " (entre externos)") if g else "")
    mejor = None
    for b in busquedas:
        if mejor is None or b["total"] < mejor["total"]:
            mejor = b
    agregar("Búsquedas frecuentes", mejor["metodo"], _tiempo(mejor["total"]) + " para 1,000 búsquedas")
    return filas


def _tiempo(seg):
    if seg >= 1:
        return f"{seg:,.2f} s"
    return f"{seg * 1000:,.2f} ms"
