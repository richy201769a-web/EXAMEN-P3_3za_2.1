"""
LIBRERIA PROPIA - REPORTE FINAL EN PDF

Genera UN solo reporte PDF con todo el proceso realizado en el sistema:
    portada y resumen, carga de datos, ordenamiento (ALGORITMO UTILIZADO y
    TIEMPO DE EJECUCION), evidencia grafica, busquedas, comparacion entre
    algoritmos, recomendaciones, laboratorio de rendimiento e intercalacion.

Diseno: cada pagina se acomoda de arriba hacia abajo con un "cursor". Las
tablas se dibujan a mano (alto exacto segun sus filas, el texto largo se
parte en varias lineas en vez de cortarse) y las graficas se estiran para
ocupar el espacio que queda, asi nada se encima ni quedan huecos.

Se dibuja con matplotlib (backend PDF). Se escribe primero a un archivo
temporal y luego se reemplaza, para no dejar PDFs a medias.
"""

import os
import time

from librerias import graficos as g
from librerias.archivos import ErrorArchivo

CARTA = (8.5, 11)              # pulgadas
AZUL_OSCURO = "#0f172a"
ACENTO = "#2563eb"
ACENTO_SUAVE = "#eff6ff"
GRIS_FILA = "#f8fafc"
BORDE = "#e2e8f0"
OK = "#15803d"
OK_SUAVE = "#f0fdf4"
ERROR = "#b91c1c"
MX = 0.07                      # margen horizontal (fraccion de la pagina)
ANCHO = 1 - 2 * MX             # ancho util
ARRIBA = 0.855                 # donde empieza el contenido bajo el encabezado
ABAJO = 0.065                  # donde termina (arriba del pie)
LINEA = 0.0145                 # alto de una linea extra de texto en una celda (8.5 pt)


def formato_tiempo(segundos):
    if segundos >= 1:
        return f"{segundos:,.3f} s"
    return f"{segundos * 1000:,.3f} ms"


# ----------------------------------------------------------------------
# Herramientas de texto
# ----------------------------------------------------------------------
def _caracteres_por_ancho(fraccion, tam, negrita=False):
    """Cuantos caracteres caben aprox. en 'fraccion' del ancho de la hoja."""
    pulgadas = fraccion * CARTA[0]
    return max(4, int(pulgadas * 72 / (tam * (0.6 if negrita else 0.52))))


def _va(texto):
    """Una linea: se alinea por la linea base (todas las celdas quedan parejas)."""
    return "center" if "\n" in texto else "center_baseline"


def _partir(texto, ancho):
    """Parte un texto en lineas de a lo mas 'ancho' caracteres (por palabras)."""
    lineas = []
    for parrafo in str(texto).split("\n"):
        actual = ""
        for palabra in parrafo.split():
            while len(palabra) > ancho * 1.35:                # solo se corta una palabra MUY larga (rutas)
                if actual:
                    lineas.append(actual)
                    actual = ""
                lineas.append(palabra[:ancho])
                palabra = palabra[ancho:]
            if actual and len(actual) + 1 + len(palabra) > ancho:
                lineas.append(actual)
                actual = palabra
            else:
                actual = (actual + " " + palabra).strip()
        lineas.append(actual)
    return "\n".join(lineas)


def _recortar(texto, largo):
    texto = str(texto)
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


# ----------------------------------------------------------------------
# Pagina con cursor vertical
# ----------------------------------------------------------------------
class Pagina:
    """Lleva la posicion vertical (y) donde se dibuja el siguiente bloque."""

    def __init__(self, fig, y=ARRIBA):
        self.fig = fig
        self.y = y

    def resto(self):
        return self.y - ABAJO

    def espacio(self, alto):
        self.y -= alto


def _figura():
    from matplotlib.figure import Figure
    fig = Figure(figsize=CARTA)
    fig.patch.set_facecolor("white")
    return fig


def _rect(fig, x, y, w, h, color, borde=None, redondeo=0.008, grosor=0.8):
    from matplotlib.patches import FancyBboxPatch
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={redondeo}",
                                      transform=fig.transFigure, facecolor=color,
                                      edgecolor=borde or color, linewidth=grosor, figure=fig))


def _linea(fig, x0, x1, y, color=BORDE, grosor=0.8):
    from matplotlib.lines import Line2D
    fig.add_artist(Line2D([x0, x1], [y, y], transform=fig.transFigure, color=color, linewidth=grosor))


def _encabezado(fig, numero, titulo, subtitulo=""):
    fig.text(MX, 0.962, "REPORTE FINAL  ·  SISTEMA DE PROCESAMIENTO Y ORDENAMIENTO MASIVO DE DATOS",
             fontsize=7, color=g.TINTA_3, fontweight="bold")
    _rect(fig, MX, 0.905, 0.042, 0.032, ACENTO, redondeo=0.006)
    fig.text(MX + 0.021, 0.921, str(numero), fontsize=12, color="white", fontweight="bold",
             ha="center", va="center")
    fig.text(MX + 0.058, 0.921, titulo, fontsize=17, color=g.TINTA, fontweight="bold", va="center")
    if subtitulo:
        fig.text(MX, 0.882, subtitulo, fontsize=9, color=g.TINTA_2)
    _linea(fig, MX, 1 - MX, 0.868)


def _pie(fig, pagina, total, fecha):
    _linea(fig, MX, 1 - MX, 0.045)
    fig.text(MX, 0.027, f"Generado el {fecha}", fontsize=7, color=g.TINTA_3)
    fig.text(1 - MX, 0.027, f"Página {pagina} de {total}", fontsize=7, color=g.TINTA_3, ha="right")


def _subtitulo(p, texto, antes=0.018):
    p.espacio(antes)
    p.fig.text(MX, p.y - 0.012, texto, fontsize=11.5, color=g.TINTA, fontweight="bold", va="center")
    p.espacio(0.034)


def _parrafo(p, texto, tam=9, color=None, x=MX, ancho=ANCHO, interlineado=None, despues=0.012):
    interlineado = interlineado or tam * 0.00205
    lineas = _partir(texto, _caracteres_por_ancho(ancho, tam)).split("\n")
    for i, linea in enumerate(lineas):
        p.fig.text(x, p.y - i * interlineado, linea, fontsize=tam, color=color or g.TINTA_2, va="top")
    p.espacio(len(lineas) * interlineado + despues)


# ----------------------------------------------------------------------
# Tablas dibujadas a mano
# ----------------------------------------------------------------------
def _preparar_tabla(filas, encabezados, anchos, tam, rh):
    """Parte el texto de cada celda para que quepa y calcula el alto de cada fila."""
    def preparar(fila, tam_txt, negrita=False):
        celdas = []
        for texto, ancho in zip(fila, anchos):
            celdas.append(_partir(texto, _caracteres_por_ancho(ancho * ANCHO - 0.024, tam_txt, negrita)))
        lineas = 1
        for c in celdas:
            n = c.count("\n") + 1
            if n > lineas:
                lineas = n
        return celdas, rh + (lineas - 1) * LINEA * tam / 8.5
    cab, alto_cab = preparar(encabezados, tam, negrita=True)
    cuerpo = [preparar(f, tam) for f in filas]
    return cab, alto_cab, cuerpo


def _alto_tabla(filas, encabezados, anchos, tam=8.5, rh=0.026):
    _cab, alto_cab, cuerpo = _preparar_tabla(filas, encabezados, anchos, tam, rh)
    return alto_cab + sum(a for _c, a in cuerpo)


def _tabla(p, filas, encabezados, anchos, tam=8.5, rh=0.026, alinear=None, colores=None, negritas=None,
           despues=0.014):
    """Dibuja la tabla en la posicion actual y baja el cursor.
    alinear: lista "l"/"r" por columna. colores(f, c) -> color de texto o None."""
    fig = p.fig
    alinear = alinear or ["l"] * len(encabezados)
    cab, alto_cab, cuerpo = _preparar_tabla(filas, encabezados, anchos, tam, rh)
    xs = [MX]
    for a in anchos[:-1]:
        xs.append(xs[-1] + a * ANCHO)
    pad = 0.012
    # Encabezado
    y = p.y
    _rect(fig, MX, y - alto_cab, ANCHO, alto_cab, AZUL_OSCURO, redondeo=0.004)
    for j, texto in enumerate(cab):
        derecha = alinear[j] == "r"
        x = xs[j] + anchos[j] * ANCHO - pad if derecha else xs[j] + pad
        fig.text(x, y - alto_cab / 2, texto, fontsize=tam, color="white", fontweight="bold",
                 ha="right" if derecha else "left", va=_va(texto), linespacing=1.15)
    y -= alto_cab
    # Filas
    for i, (celdas, alto) in enumerate(cuerpo):
        if i % 2 == 1:
            _rect(fig, MX, y - alto, ANCHO, alto, GRIS_FILA, redondeo=0)
        for j, texto in enumerate(celdas):
            derecha = alinear[j] == "r"
            x = xs[j] + anchos[j] * ANCHO - pad if derecha else xs[j] + pad
            color = colores(i, j) if colores else None
            negrita = bool(color) or (negritas is not None and j in negritas)
            fig.text(x, y - alto / 2, texto, fontsize=tam, color=color or g.TINTA,
                     fontweight="bold" if negrita else "normal",
                     ha="right" if derecha else "left", va=_va(texto), linespacing=1.15)
        y -= alto
        _linea(fig, MX, 1 - MX, y, grosor=0.6)
    p.y = y - despues


# ----------------------------------------------------------------------
# Otros bloques
# ----------------------------------------------------------------------
def _grafica(p, alto, dibujar, izq=0.085, abajo=0.05, arriba=0.03, der=0.0, despues=0.01):
    """Reserva 'alto' de la pagina y llama dibujar(fig, rect) con el area de los ejes."""
    if alto - abajo - arriba < 0.06:                       # no hay lugar: no se dibuja una grafica aplastada
        return
    rect = [MX + izq, p.y - alto + abajo, ANCHO - izq - der, alto - abajo - arriba]
    dibujar(p.fig, rect)
    p.espacio(alto + despues)


def _kpis(p, kpis, alto=0.085):
    n = len(kpis)
    sep = 0.025
    ancho = (ANCHO - sep * (n - 1)) / n
    for i, (etiqueta, valor, color) in enumerate(kpis):
        x = MX + i * (ancho + sep)
        y = p.y - alto
        _rect(p.fig, x, y, ancho, alto, "white", borde=BORDE)
        _rect(p.fig, x, y + alto - 0.006, ancho, 0.006, color or ACENTO, redondeo=0.002)
        p.fig.text(x + 0.015, y + alto - 0.03, etiqueta.upper(), fontsize=7, color=g.TINTA_3, fontweight="bold")
        p.fig.text(x + 0.015, y + 0.022, _recortar(valor, 18), fontsize=13, color=color or g.TINTA,
                   fontweight="bold")
    p.espacio(alto + 0.02)


def _caja(p, titulo, lineas, fondo=ACENTO_SUAVE, acento=ACENTO, tam=9):
    """Recuadro de color con titulo y vinetas; su alto se ajusta al texto."""
    interlineado = tam * 0.00205
    partes = [_partir(l, _caracteres_por_ancho(ANCHO - 0.07, tam)).split("\n") for l in lineas]
    total_lineas = sum(len(x) for x in partes)
    alto = 0.05 + total_lineas * interlineado + len(partes) * 0.004
    y0 = p.y - alto
    _rect(p.fig, MX, y0, ANCHO, alto, fondo, redondeo=0.006)
    _rect(p.fig, MX, y0, 0.005, alto, acento, redondeo=0)
    p.fig.text(MX + 0.025, p.y - 0.022, titulo, fontsize=10.5, color=acento, fontweight="bold", va="center")
    y = p.y - 0.045
    for linea in partes:
        p.fig.text(MX + 0.028, y, "•", fontsize=tam, color=acento, fontweight="bold", va="top")
        for k, texto in enumerate(linea):
            p.fig.text(MX + 0.045, y - k * interlineado, texto, fontsize=tam, color=g.TINTA, va="top")
        y -= len(linea) * interlineado + 0.004
    p.espacio(alto + 0.018)


def _tarjetas(p, tarjetas, alto=0.105):
    """Fila de tarjetas (titulo, valor grande, nota de hasta dos lineas)."""
    n = len(tarjetas)
    sep = 0.02
    ancho = (ANCHO - sep * (n - 1)) / n
    for i, (titulo, valor, nota) in enumerate(tarjetas):
        x = MX + i * (ancho + sep)
        y = p.y - alto
        _rect(p.fig, x, y, ancho, alto, GRIS_FILA, borde=BORDE)
        _rect(p.fig, x, y, 0.004, alto, ACENTO, redondeo=0)
        p.fig.text(x + 0.018, y + alto - 0.02, titulo, fontsize=9.5, color=g.TINTA, fontweight="bold",
                   va="center_baseline")
        p.fig.text(x + 0.018, y + alto - 0.048, valor, fontsize=14, color=ACENTO, fontweight="bold",
                   va="center_baseline")
        lineas = _partir(nota, _caracteres_por_ancho(ancho - 0.03, 7.5)).split("\n")[:2]
        p.fig.text(x + 0.018, y + 0.012, "\n".join(lineas), fontsize=7.5, color=g.TINTA_2, va="bottom",
                   linespacing=1.25)
    p.espacio(alto + 0.012)


def _bloques_de_20(lista):
    primeros = lista[:20]
    ultimos = lista[-20:] if len(lista) > 20 else []
    inicio_ult = len(lista) - len(ultimos)
    filas = []
    for i in range(20):
        a = (f"{i + 1:,}", f"{primeros[i]:,}") if i < len(primeros) else ("", "")
        b = (f"{inicio_ult + i + 1:,}", f"{ultimos[i]:,}") if i < len(ultimos) else ("", "")
        filas.append([a[0], a[1], b[0], b[1]])
    return filas


# ----------------------------------------------------------------------
# Paginas
# ----------------------------------------------------------------------
def _pagina_portada(fig, info):
    r = info["resultado"]
    a = info["archivo"]
    _rect(fig, 0, 0.75, 1, 0.25, AZUL_OSCURO, redondeo=0)
    _rect(fig, 0, 0.75, 1, 0.006, ACENTO, redondeo=0)
    fig.text(MX, 0.93, "ESTRUCTURA DE DATOS  ·  ALGORITMOS DE ORDENAMIENTO Y BÚSQUEDA", fontsize=8,
             color="#93c5fd", fontweight="bold")
    fig.text(MX, 0.875, "Reporte final de procesamiento", fontsize=25, color="white", fontweight="bold")
    fig.text(MX, 0.838, "Sistema de Procesamiento y Ordenamiento Masivo de Datos", fontsize=12, color="#cbd5e1")
    fig.text(MX, 0.785, f'Archivo: {_recortar(a["nombre"], 60)}   ·   Fecha: {info["fecha"]}', fontsize=9,
             color="#94a3b8")

    p = Pagina(fig, 0.715)
    _kpis(p, [("Registros", f'{a["n"]:,}', None),
              ("Algoritmo utilizado", r["algoritmo"], None),
              ("Tiempo de ejecución", formato_tiempo(r["segundos"]), None),
              ("Verificación", "✔ Ordenado" if r["verificado"] else "✘ No ordenado",
               OK if r["verificado"] else ERROR)])
    _subtitulo(p, "Resumen del proceso", antes=0.005)
    filas = []
    for nombre, hecho, detalle, obligatorio in info["pasos"]:
        estado = "✔ Completado" if hecho else ("Pendiente" if obligatorio else "No realizado (opcional)")
        filas.append([nombre, estado, detalle])
    _tabla(p, filas, ["Paso", "Estado", "Detalle"], [0.27, 0.23, 0.5], rh=0.027,
           colores=lambda f, c: (OK if filas[f][1].startswith("✔") else g.TINTA_3) if c == 1 else None)
    if info.get("conclusiones"):
        _caja(p, "Hallazgos principales", info["conclusiones"][:3])
    _subtitulo(p, "Contenido", antes=0.0)
    secciones = info["secciones"]
    mitad = (len(secciones) + 1) // 2
    y0 = p.y
    for i, titulo in enumerate(secciones):
        col = 0 if i < mitad else 1
        fila = i if i < mitad else i - mitad
        x = MX + col * ANCHO / 2
        y = y0 - fila * 0.024
        fig.text(x + 0.005, y, f"{i + 1}.", fontsize=9.5, color=ACENTO, fontweight="bold", va="top")
        fig.text(x + 0.035, y, titulo, fontsize=9.5, color=g.TINTA, va="top")


def _pagina_carga(fig, info):
    a = info["archivo"]
    p = Pagina(fig)
    filas = [
        ["Archivo", a["nombre"]],
        ["Formato", a["formato"]],
        ["Encabezado / hoja", a["detalle_hoja"]],
        ["Tamaño", f'{a["bytes"] / 1024:,.1f} KB'],
        ["Total de registros", f'{a["n"]:,}'],
        ["Valor mínimo / máximo", f'{a["minimo"]:,}  /  {a["maximo"]:,}'],
        ["Valores distintos / repetidos", f'{a["distintos"]:,}  /  {a["repetidos"]:,}'],
        ["Estado inicial", a["estado_inicial"]],
        ["Tiempo de lectura y validación", formato_tiempo(a["segundos_lectura"])],
    ]
    _tabla(p, filas, ["Concepto", "Valor"], [0.36, 0.64], tam=9, rh=0.028, negritas=[0])
    _subtitulo(p, "Distribución de los datos cargados (posición → valor)")
    _grafica(p, p.resto(), lambda f, rect: g.dibujar_datos(f, info["original"], rect=rect))


def _pagina_ordenamiento(fig, info):
    r = info["resultado"]
    p = Pagina(fig)
    filas = [
        ["Algoritmo utilizado", r["algoritmo"]],
        ["Tipo de ordenamiento", "Interno (en memoria)" if r["tipo"] == "Interno" else "Externo (en archivos)"],
        ["Orden", r["orden"]],
        ["Tiempo de ejecución", formato_tiempo(r["segundos"])],
        ["Comparaciones", f'{r["comparaciones"]:,}'],
        ["Movimientos / escrituras", f'{r["movimientos"]:,}'],
        ["Pasadas sobre archivos", f'{r["pasadas"]:,}' if r["tipo"] == "Externo" else "No aplica"],
        ["Total de registros", f'{r["n"]:,}'],
        ["Verificación", "✔ El resultado está correctamente ordenado" if r["verificado"] else "✘ NO está ordenado"],
    ]
    _tabla(p, filas, ["Concepto", "Valor"], [0.36, 0.64], tam=9, rh=0.027, negritas=[0],
           colores=lambda f, c: (OK if r["verificado"] else ERROR) if (f == 8 and c == 1) else None)
    _subtitulo(p, "Primeros 20 y últimos 20 elementos ordenados")
    rh = (p.resto() - 0.026 - 0.005) / 20                  # las 20 filas llenan exactamente el resto
    rh = max(0.017, min(0.024, rh))
    _tabla(p, _bloques_de_20(r["lista"]), ["Posición", "Primeros 20", "Posición", "Últimos 20"],
           [0.18, 0.32, 0.18, 0.32], tam=8.5, rh=rh, alinear=["r", "r", "r", "r"], despues=0)


def _pagina_evidencia(fig, info):
    p = Pagina(fig, ARRIBA - 0.005)
    alto = p.resto() / 2
    _grafica(p, alto, lambda f, rect: _panel_antes(f, rect, info), arriba=0.035)
    _grafica(p, p.resto(), lambda f, rect: _panel_despues(f, rect, info), arriba=0.035)


def _panel_antes(fig, rect, info):
    ax = fig.add_axes(rect)
    g._estilo_ejes(ax)
    escala = _escala_resultado(info)
    xs, ys = g._muestra(info["original"])
    ax.scatter(xs, escala.transformar(ys), s=3, color=g.NARANJA, alpha=0.55, linewidths=0, zorder=2)
    _ejes_posicion_valor(ax, "Antes · datos originales", escala, len(info["original"]))


def _panel_despues(fig, rect, info):
    ax = fig.add_axes(rect)
    g._estilo_ejes(ax)
    escala = _escala_resultado(info)
    xs, ys = g._muestra(info["resultado"]["lista"])
    ax.plot(xs, escala.transformar(ys), color=g.AZUL, linewidth=2, zorder=2,
            marker="o" if len(xs) == 1 else None, markersize=4)
    _ejes_posicion_valor(ax, "Después · datos ordenados (" + info["resultado"]["orden"].lower() + ")", escala,
                         len(info["resultado"]["lista"]))


def _escala_resultado(info):
    """La misma escala dinamica para los dos paneles (calculada con los datos ordenados)."""
    ordenada = info["resultado"]["lista"]
    return g.escala_valores(ordenada, ordenada)


def _ejes_posicion_valor(ax, titulo, escala, n):
    g._titulo(ax, titulo)
    g.eje_posiciones(ax, n)
    escala.aplicar(ax)


def _pagina_busquedas(fig, info):
    p = Pagina(fig)
    busq = info["busquedas"]

    def fila(b):
        fuente = str(b["fuente"]).replace("datos ordenados con ", "ordenados · ").replace("datos originales ",
                                                                                          "originales ")
        return [f'{b["valor"]:,}', b["metodo"], "✔ Encontrado" if b["encontrado"] else "✘ No encontrado",
                f'{b["apariciones"]:,}', f'{b["comparaciones"]:,}', formato_tiempo(b["segundos"]), fuente]
    encabezados = ["Valor", "Método", "Resultado", "Apariciones", "Comparac.", "Tiempo", "Buscado en"]
    anchos = [0.085, 0.105, 0.15, 0.135, 0.12, 0.1, 0.305]
    mostrar = busq[-12:]                                  # las ultimas que quepan en 0.36 de la hoja
    while len(mostrar) > 1 and _alto_tabla([fila(b) for b in mostrar], encabezados, anchos, 8, 0.024) > 0.36:
        mostrar = mostrar[1:]
    if len(busq) > len(mostrar):
        _parrafo(p, f"Se realizaron {len(busq):,} búsquedas; se muestran las últimas {len(mostrar)}.",
                 despues=0.008)
    filas = [fila(b) for b in mostrar]
    _tabla(p, filas, encabezados, anchos, tam=8, rh=0.024,
           alinear=["r", "l", "l", "r", "r", "r", "l"],
           colores=lambda f, c: (OK if filas[f][2].startswith("✔") else ERROR) if c == 2 else None)
    cb = info.get("comparacion_busquedas")
    complejidad = {"Secuencial": ("O(n)", "Revisa los datos uno por uno"),
                   "Binaria": ("O(log n)", "Descarta la mitad en cada paso"),
                   "Hash": ("O(1) promedio", "Revisa una sola cubeta de la tabla")}
    reservado = 0.17                                      # lugar para las tarjetas de complejidad
    if cb:
        _subtitulo(p, f'Comparaciones de cada método para el valor {cb["valor"]:,}')
        alto = min(0.3, p.resto() - reservado)            # barras de grosor razonable
        _grafica(p, alto, lambda f, rect: g.dibujar_busquedas(f, cb["filas"], rect=rect), izq=0.1)
        tarjetas = [(m, f"{c:,} comp.", f"{complejidad[m][0]} · {complejidad[m][1]}") for m, c, _s, _a in cb["filas"]]
    else:
        tarjetas = [(m, complejidad[m][0], complejidad[m][1]) for m in ("Secuencial", "Binaria", "Hash")]
    _subtitulo(p, "Complejidad de cada método", antes=0.0)
    _tarjetas(p, tarjetas)
    if p.resto() > 0.13:                                  # si sobra espacio, se explica la diferencia
        n = info["archivo"]["n"]
        pasos = 1
        while (1 << pasos) < n:
            pasos += 1
        _caja(p, "¿Por qué hay tanta diferencia?", [
            f"Secuencial: compara el valor contra cada dato; con {n:,} datos puede necesitar {n:,} comparaciones.",
            f"Binaria: cada comparación descarta la mitad de los datos que quedan; con {n:,} datos bastan unas "
            f"{pasos} (log₂ n), pero solo funciona si los datos están ordenados.",
            "Hash: calcula la cubeta con valor mod tamaño de la tabla y solo revisa esa cubeta; construir la tabla "
            "cuesta O(n) una sola vez, después cada búsqueda es casi inmediata.",
        ])


def _pagina_comparacion(fig, info):
    res = info["comparacion"]
    p = Pagina(fig)
    _parrafo(p, f'Todos los algoritmos ordenaron los mismos {info["archivo"]["n"]:,} registros en orden '
                f'{info["comparacion_orden"].lower()}. Azul = ordenamiento interno (en memoria); '
                'naranja = ordenamiento externo (en archivos). El más rápido aparece arriba.')
    filas = [[r["algoritmo"], r["tipo"], formato_tiempo(r["segundos"]), f'{r["comparaciones"]:,}',
              f'{r["movimientos"]:,}', "✔" if r["verificado"] else "✘"] for r in res]
    encabezados = ["Algoritmo", "Tipo", "Tiempo", "Comparaciones", "Movimientos", "Ordenado"]
    anchos = [0.25, 0.13, 0.16, 0.18, 0.16, 0.12]
    alto_tabla = _alto_tabla(filas, encabezados, anchos, 8.5, 0.026)
    _grafica(p, p.resto() - alto_tabla - 0.02, lambda f, rect: g.dibujar_comparacion(f, res, rect=rect),
             izq=0.16, arriba=0.045)
    p.y = ABAJO + alto_tabla
    _tabla(p, filas, encabezados, anchos, rh=0.026, alinear=["l", "l", "r", "r", "r", "l"], despues=0,
           colores=lambda f, c: (OK if filas[f][5] == "✔" else ERROR) if c == 5 else None)


def _pagina_recomendaciones(fig, info):
    p = Pagina(fig)
    filas = [[e, a, m] for e, a, m in info["recomendaciones"]]
    _tabla(p, filas, ["Escenario", "Algoritmo recomendado", "Motivo"], [0.22, 0.21, 0.57], tam=9.5, rh=0.036,
           negritas=[1])
    if info.get("conclusiones"):
        _subtitulo(p, "Conclusiones observadas", antes=0.02)
        for linea in info["conclusiones"]:
            p.fig.text(MX + 0.004, p.y, "•", fontsize=11, color=ACENTO, fontweight="bold", va="top")
            _parrafo(p, linea, tam=10, color=g.TINTA, x=MX + 0.025, ancho=ANCHO - 0.025, despues=0.012)


def _pagina_lab_escalabilidad(fig, info):
    L = info["laboratorio"]
    p = Pagina(fig)
    _parrafo(p, f'Cada algoritmo se midió con tamaños crecientes de los mismos datos (hasta {L["n"]:,}). '
                'En escala logarítmica, la pendiente de cada línea es el exponente b de t ≈ n^b: duplicar n '
                'multiplica el tiempo por 2^b. b ≈ 2 indica O(n²); b ≈ 1 indica O(n log n) o lineal.')
    filas = [[s["algoritmo"], f'{s["exponente"]:.2f}' if s["exponente"] is not None else "—",
              s["interpretacion"], s["teorica"], f'{s["puntos"][-1][0]:,}'] for s in L["series"]]
    encabezados = ["Algoritmo", "b medido", "Crecimiento medido", "Complejidad teórica", "n máximo"]
    anchos = [0.19, 0.125, 0.275, 0.3, 0.11]
    alto_tabla = _alto_tabla(filas, encabezados, anchos, 8, 0.024)
    _grafica(p, p.resto() - alto_tabla - 0.02, lambda f, rect: g.dibujar_escalabilidad(f, L["series"], rect=rect),
             izq=0.08, der=0.27)
    p.y = ABAJO + alto_tabla
    _tabla(p, filas, encabezados, anchos, tam=8, rh=0.024, alinear=["l", "r", "l", "l", "r"], despues=0)


def _pagina_lab_escenarios(fig, info):
    L = info["laboratorio"]
    p = Pagina(fig)
    filas_r = [[r["escenario"], r["ganador"], r["detalle"], r["teorica"], "✔ Sí" if r["coincide"] else "✘ No"]
               for r in L["recomendaciones"]]
    enc_r = ["Escenario", "Ganador medido", "Tiempo", "Recomendación teórica", "¿Coincide?"]
    anc_r = [0.24, 0.18, 0.24, 0.22, 0.12]
    filas_b = [[b["metodo"], formato_tiempo(b["preparacion"]), formato_tiempo(b["por_busqueda"]),
                formato_tiempo(b["total"]), b["nota"]] for b in L["busquedas"]]
    enc_b = ["Búsqueda", "Preparación", "Por búsqueda", "Total 1,000", "Nota"]
    anc_b = [0.15, 0.15, 0.16, 0.16, 0.38]
    reservado = (_alto_tabla(filas_r, enc_r, anc_r, 8, 0.024) + _alto_tabla(filas_b, enc_b, anc_b, 8, 0.024)
                 + 2 * 0.052 + 0.02)
    _subtitulo(p, "Tiempo por escenario (ms) · borde verde = ganador de la fila", antes=0.0)
    _grafica(p, p.resto() - reservado,
             lambda f, rect: g.dibujar_matriz(f, L["escenarios"], L["nombres"], L["matriz"], rect=rect),
             izq=0.2, abajo=0.085, arriba=0.005)
    _subtitulo(p, "Recomendación comprobada con mediciones", antes=0.004)
    _tabla(p, filas_r, enc_r, anc_r, tam=8, rh=0.024,
           colores=lambda f, c: (OK if filas_r[f][4].startswith("✔") else ERROR) if c == 4 else None)
    _subtitulo(p, "Búsquedas frecuentes: costo de 1,000 búsquedas (incluye preparación)", antes=0.0)
    _tabla(p, filas_b, enc_b, anc_b, tam=8, rh=0.024, alinear=["l", "r", "r", "r", "l"], despues=0)


def _pagina_intercalacion(fig, info):
    it = info["intercalacion"]
    p = Pagina(fig)
    filas = [["Archivo A", it["a"]], ["Archivo B", it["b"]], ["Archivo resultado", it["salida"]],
             ["Orden", it["orden"]], ["Total de registros", f'{it["n"]:,}'],
             ["Comparaciones", f'{it["comparaciones"]:,}'], ["Tiempo", formato_tiempo(it["segundos"])],
             ["Verificación", "✔ Resultado ordenado" if it["verificado"] else "✘ Resultado NO ordenado"]]
    _tabla(p, filas, ["Concepto", "Valor"], [0.32, 0.68], tam=9, rh=0.028, negritas=[0],
           colores=lambda f, c: (OK if it["verificado"] else ERROR) if (f == 7 and c == 1) else None)
    _subtitulo(p, "Archivo intercalado (posición → valor)")
    _grafica(p, p.resto(), lambda f, rect: g.dibujar_datos(f, it["datos"], color=g.AZUL, rect=rect))


# ----------------------------------------------------------------------
# Reporte final
# ----------------------------------------------------------------------
def reporte_final(ruta, info):
    """Genera el reporte final. 'info' lo arma la interfaz con todo lo que
    se hizo en la sesion (ver Aplicacion._info_reporte_final)."""
    if os.path.splitext(ruta)[1].lower() != ".pdf":
        raise ErrorArchivo("El reporte debe guardarse con extensión .pdf")
    info = dict(info)
    info["fecha"] = time.strftime("%d/%m/%Y %H:%M:%S")

    paginas = [("Carga de datos", "Archivo leído, validado y sus características", _pagina_carga),
               ("Ordenamiento", "Algoritmo utilizado, tiempo de ejecución y resultados", _pagina_ordenamiento),
               ("Evidencia gráfica del ordenamiento", "Los mismos datos antes y después de ordenar",
                _pagina_evidencia),
               ("Búsquedas realizadas", "Métodos secuencial, binaria y hash", _pagina_busquedas),
               ("Comparación entre algoritmos", "Tiempo de ejecución con los mismos datos", _pagina_comparacion),
               ("Algoritmo recomendado por escenario", "Comparación básica y conclusiones",
                _pagina_recomendaciones)]
    if info.get("laboratorio"):
        paginas.append(("Laboratorio: escalabilidad", "Exponente de crecimiento medido de cada algoritmo",
                        _pagina_lab_escalabilidad))
        paginas.append(("Laboratorio: escenarios", "El requerimiento 6 comprobado con mediciones reales",
                        _pagina_lab_escenarios))
    if info.get("intercalacion"):
        paginas.append(("Intercalación de archivos", "Unión de dos archivos ordenados (ordenamiento externo)",
                        _pagina_intercalacion))
    info["secciones"] = [t[0] for t in paginas]
    total = len(paginas) + 1

    from matplotlib.backends.backend_pdf import PdfPages
    temporal = ruta + ".tmp"
    try:
        pdf = PdfPages(temporal, metadata={"Title": "Reporte final de procesamiento",
                                           "Subject": "Sistema de Procesamiento y Ordenamiento Masivo de Datos"})
    except OSError as e:
        raise ErrorArchivo(f"No se pudo crear el PDF: {e.strerror or e}")
    try:
        fig = _figura()
        _pagina_portada(fig, info)
        _pie(fig, 1, total, info["fecha"])
        pdf.savefig(fig)
        for i, (titulo, subtitulo, dibujar) in enumerate(paginas):
            fig = _figura()
            _encabezado(fig, i + 1, titulo, subtitulo)
            dibujar(fig, info)
            _pie(fig, i + 2, total, info["fecha"])
            pdf.savefig(fig)
        pdf.close()
    except Exception:
        try:
            pdf.close()
        except Exception:
            pass
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise
    try:
        os.replace(temporal, ruta)
    except PermissionError:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise ErrorArchivo("No se pudo guardar el PDF: está abierto en otro programa o no hay permiso.")
