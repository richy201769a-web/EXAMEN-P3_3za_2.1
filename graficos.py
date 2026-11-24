"""
LIBRERIA PROPIA - GRAFICOS (matplotlib)

Dibuja sobre objetos Figure de matplotlib. Las mismas funciones se usan en
la interfaz (dentro de la ventana) y en el reporte PDF, asi lo que se ve en
pantalla es exactamente lo que se exporta.

matplotlib solo DIBUJA: no se usa para ordenar nada.
"""

import warnings

# Paleta (validada para daltonismo): azul = principal / interno,
# naranja = secundario / externo.
AZUL = "#2a78d6"
NARANJA = "#eb6834"
VERDE = "#15803d"
TINTA = "#0f172a"
TINTA_2 = "#475569"
TINTA_3 = "#94a3b8"
REJILLA = "#e2e8f0"
FONDO = "#ffffff"


def _configurar_fuentes():
    """Usa Segoe UI si existe (Windows); si no, la fuente por defecto."""
    try:
        import matplotlib
        from matplotlib import font_manager
        disponibles = set(f.name for f in font_manager.fontManager.ttflist)
        familia = []
        for nombre in ("Segoe UI", "DejaVu Sans"):          # DejaVu aporta simbolos como ✔
            if nombre in disponibles:
                familia.append(nombre)
        if familia:
            matplotlib.rcParams["font.family"] = familia
        matplotlib.rcParams["axes.titlepad"] = 10
        import logging
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    except Exception:
        pass


_configurar_fuentes()


def _estilo_ejes(ax):
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.tick_params(colors=TINTA_2, labelsize=8, length=0, pad=6)
    ax.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def _miles(x, _pos=None):
    return f"{int(x):,}"


def _formatear_eje_miles(eje, n=None):
    """Marcas en numeros enteros (posiciones y valores siempre son enteros).
    n = cantidad de posiciones del eje X (con un solo dato se abre el rango)."""
    from matplotlib.ticker import FuncFormatter, MaxNLocator
    eje.set_major_locator(MaxNLocator(nbins=6, integer=True))
    eje.set_major_formatter(FuncFormatter(_miles))
    if n is not None and n <= 1:
        eje.axes.set_xlim(-1, 1)


# Hasta esta cantidad de datos se dibujan TODOS los puntos.
MAX_PUNTOS = 40000


def _muestra(lista, maximo=MAX_PUNTOS):
    """Puntos a dibujar: (posiciones desde 1, valores).

    Hasta 'maximo' datos se dibujan todos. Con mas (archivos de cientos de
    miles) se divide la lista en tramos y de cada tramo se dibujan su menor y
    su mayor valor: la grafica sigue cubriendo de la posicion 1 a la n y
    ningun valor extremo desaparece. Solo sirve para DIBUJAR.
    """
    n = len(lista)
    if n <= maximo:
        return list(range(1, n + 1)), list(lista)
    tramos = maximo // 2
    xs = []
    ys = []
    for k in range(tramos):
        ini = k * n // tramos
        fin = (k + 1) * n // tramos
        i_min = i_max = ini
        for i in range(ini + 1, fin):
            if lista[i] < lista[i_min]:
                i_min = i
            if lista[i] > lista[i_max]:
                i_max = i
        primero, segundo = (i_min, i_max) if i_min <= i_max else (i_max, i_min)
        xs.append(primero + 1)
        ys.append(lista[primero])
        if segundo != primero:
            xs.append(segundo + 1)
            ys.append(lista[segundo])
    if xs[0] != 1:                                   # la primera y la ultima posicion siempre
        xs.insert(0, 1)
        ys.insert(0, lista[0])
    if xs[-1] != n:
        xs.append(n)
        ys.append(lista[-1])
    return xs, ys


def _muestra_escala(lista, maximo=4000):
    """Muestra uniforme (1 de cada k) mas el menor y el mayor: sirve para
    estimar el rango tipico sin ordenar listas enormes."""
    n = len(lista)
    if n <= maximo:
        return list(lista)
    paso = n // maximo + 1
    valores = [lista[i] for i in range(0, n, paso)]
    menor = mayor = lista[0]
    for v in lista:
        if v < menor:
            menor = v
        if v > mayor:
            mayor = v
    valores.append(menor)
    valores.append(mayor)
    return valores


def eje_posiciones(ax, n, etiqueta="Posición"):
    """Eje X de 1 a n (la cantidad real de datos procesados). La ultima marca
    es exactamente n, para que se vea el total."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    n = max(int(n), 1)
    marcas = [1]
    if n > 1:
        paso = _paso_bonito(n / 5)
        v = paso
        while v < n:
            if v - 1 >= n * 0.08 and n - v >= n * 0.08:     # no encimar con 1 ni con n
                marcas.append(v)
            v += paso
        marcas.append(n)
    ax.xaxis.set_major_locator(FixedLocator(marcas))
    ax.xaxis.set_major_formatter(FuncFormatter(_miles))
    ax.xaxis.set_minor_locator(NullLocator())
    margen = n * 0.015 if n * 0.015 > 0.6 else 0.6
    ax.set_xlim(1 - margen, n + margen)
    if etiqueta:
        ax.set_xlabel(etiqueta, fontsize=8, color=TINTA_2)


# ----------------------------------------------------------------------
# Escala dinamica del eje de valores
# ----------------------------------------------------------------------
# El "grueso" de los datos es lo que hay entre el 2% y el 98% (ya ordenado).
# Un valor que queda a mas de FACTOR_EXTREMO anchos del grueso es extremo: si
# se usara escala lineal aplastaria todo lo demas en una linea.
FACTOR_EXTREMO = 2
COMPRESION_MAX = 0.25      # cada potencia de 10 fuera del grueso ocupa como maximo 1/4 del ancho
ZONA_EXTREMA_MAX = 0.7     # y toda la zona comprimida de un lado, como maximo 0.7 anchos


def _paso_bonito(x):
    """1, 2 o 5 x 10^k mas cercano hacia arriba (minimo 1: los datos son enteros)."""
    if x <= 1:
        return 1
    p = 1
    while p * 10 <= x:
        p *= 10
    for m in (1, 2, 5, 10):
        if m * p >= x:
            return m * p
    return 10 * p


def _candidatos_bonitos(desde, hasta):
    """Numeros 'redondos' (+-1, 2, 5 x 10^k y el 0) dentro de (desde, hasta], en orden creciente."""
    positivos = []
    p = 1
    while p <= 10 ** 16:
        for m in (1, 2, 5):
            positivos.append(m * p)
        p *= 10
    res = []
    for i in range(len(positivos) - 1, -1, -1):
        if desde < -positivos[i] <= hasta:
            res.append(-positivos[i])
    if desde < 0 <= hasta:
        res.append(0)
    for v in positivos:
        if desde < v <= hasta:
            res.append(v)
    return res


class EscalaValores:
    """Escala del eje de valores calculada a partir de los propios datos.

    * Sin valores extremos: lineal y ajustada al minimo y maximo reales.
    * Con valores extremos: el grueso de los datos queda en escala lineal y
      ocupa la mayor parte de la grafica; lo que queda fuera se comprime en
      escala logaritmica. Las etiquetas del eje siempre muestran valores reales.
    Funciona con negativos, con datos lejos del 0 y en orden ascendente o
    descendente. Solo sirve para DIBUJAR; no ordena nada.
    """

    def __init__(self, ordenados):
        a, b = ordenados[0], ordenados[-1]
        self.minimo, self.maximo = (a, b) if a <= b else (b, a)
        self.bajo, self.alto = self.minimo, self.maximo
        self.arriba = self.abajo = False
        n = len(ordenados)
        if n >= 4:
            i_bajo = int(0.02 * (n - 1))                # posiciones del 2% y del 98% de menor a mayor
            i_alto = int(0.98 * (n - 1))
            if a > b:                                   # la lista viene descendente: se cuenta desde el final
                i_bajo, i_alto = n - 1 - i_bajo, n - 1 - i_alto
            p_bajo = ordenados[i_bajo]
            p_alto = ordenados[i_alto]
            ancho = max(p_alto - p_bajo, 1)
            if self.maximo > p_alto + FACTOR_EXTREMO * ancho:
                self.alto, self.arriba = p_alto, True
            if self.minimo < p_bajo - FACTOR_EXTREMO * ancho:
                self.bajo, self.abajo = p_bajo, True
        self.ancho = max(self.alto - self.bajo, 1)
        self.c_arriba = self._compresion(self.maximo - self.alto) if self.arriba else 0
        self.c_abajo = self._compresion(self.bajo - self.minimo) if self.abajo else 0

    @property
    def comprimida(self):
        return self.arriba or self.abajo

    def _compresion(self, distancia):
        decadas = _log10(1 + distancia / self.ancho)
        if decadas <= 0:
            return COMPRESION_MAX
        c = ZONA_EXTREMA_MAX / decadas
        return c if c < COMPRESION_MAX else COMPRESION_MAX

    def t(self, v):
        """Posicion en el eje para el valor real v (creciente: respeta el orden)."""
        if self.arriba and v > self.alto:
            return self.alto + self.ancho * self.c_arriba * _log10(1 + (v - self.alto) / self.ancho)
        if self.abajo and v < self.bajo:
            return self.bajo - self.ancho * self.c_abajo * _log10(1 + (self.bajo - v) / self.ancho)
        return v

    def transformar(self, valores):
        if not self.comprimida:
            return valores
        return [self.t(v) for v in valores]

    def marcas(self):
        """[(posicion, etiqueta)] en orden creciente, sin marcas encimadas."""
        total = self.t(self.maximo) - self.t(self.minimo)
        separacion = total * 0.11
        paso = _paso_bonito((self.alto - self.bajo) / 5)
        lineales = []
        v = -((-self.bajo) // paso) * paso              # primer multiplo de paso >= bajo
        while v <= self.alto:
            lineales.append(v)
            v += paso
        if not lineales:
            lineales = [self.bajo]
        abajo = []
        if self.abajo:
            ultimo = self.t(lineales[0])
            cand = _candidatos_bonitos(self.minimo - 1, self.bajo - 1)
            for i in range(len(cand) - 1, -1, -1):          # del mas cercano al mas lejano
                if ultimo - self.t(cand[i]) >= separacion:
                    abajo.append(cand[i])
                    ultimo = self.t(cand[i])
        arriba = []
        if self.arriba:
            ultimo = self.t(lineales[-1])
            for c in _candidatos_bonitos(self.alto, self.maximo):
                if self.t(c) - ultimo >= separacion:
                    arriba.append(c)
                    ultimo = self.t(c)
        valores = [abajo[i] for i in range(len(abajo) - 1, -1, -1)] + lineales + arriba
        return [(self.t(v), _miles(v)) for v in self._con_extremos(valores)]

    def _con_extremos(self, valores):
        """Agrega el menor y el mayor valor REALES como primera y ultima marca y
        quita las marcas que quedarian encimadas con ellos."""
        if self.minimo == self.maximo:
            return [self.minimo]
        t_min, t_max = self.t(self.minimo), self.t(self.maximo)
        cerca = (t_max - t_min) * 0.08
        res = [self.minimo]
        for v in valores:
            if self.minimo < v < self.maximo and self.t(v) - t_min >= cerca and t_max - self.t(v) >= cerca:
                res.append(v)
        res.append(self.maximo)
        return res

    def aplicar(self, ax, etiqueta="Valor"):
        """Pone limites, marcas y etiqueta del eje Y. El eje va exactamente del
        menor al mayor valor de los datos (con un pequeno margen) y ambos
        aparecen como marcas."""
        from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
        marcas = self.marcas()
        ax.yaxis.set_major_locator(FixedLocator([p for p, _ in marcas]))
        ax.yaxis.set_major_formatter(FixedFormatter([e for _, e in marcas]))
        ax.yaxis.set_minor_locator(NullLocator())
        y0, y1 = self.t(self.minimo), self.t(self.maximo)
        margen = (y1 - y0) * 0.05 if y1 > y0 else 1
        ax.set_ylim(y0 - margen, y1 + margen)
        if self.comprimida:
            for limite, usado in ((self.alto, self.arriba), (self.bajo, self.abajo)):
                if usado:                                    # donde empieza la zona comprimida
                    ax.axhline(limite, color=TINTA_3, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
            if etiqueta:
                etiqueta += " · escala ajustada (extremos comprimidos)"
        if etiqueta:
            ax.set_ylabel(etiqueta, fontsize=8, color=TINTA_2)


def escala_valores(datos, ordenados=None):
    """Escala para graficar 'datos'. Si ya se tiene la version ordenada se
    usa; si no, se ordena una muestra (con los extremos) con nuestro QuickSort."""
    if ordenados is None:
        from librerias.ordenamiento_interno import quick_sort
        ordenados, _est = quick_sort(_muestra_escala(datos))
    return EscalaValores(ordenados)


def _ajustar(fig):
    """tight_layout solo en figuras completas; se ignoran avisos si la
    ventana es muy pequena."""
    if hasattr(fig, "tight_layout"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig.tight_layout()


def _vacio(ax, texto):
    ax.text(0.5, 0.5, texto, ha="center", va="center", color=TINTA_3, fontsize=10, transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)


def _ejes(fig, rect):
    if rect is None:
        fig.clear()
        fig.patch.set_facecolor(FONDO)
        return fig.add_subplot(111)
    return fig.add_axes(rect)


def _titulo(ax, titulo):
    if titulo:
        ax.set_title(titulo, loc="left", fontsize=10, color=TINTA, fontweight="bold")


# ----------------------------------------------------------------------
# Datos cargados
# ----------------------------------------------------------------------
def dibujar_datos(fig, datos, titulo="", color=NARANJA, rect=None):
    """Dispersion posicion -> valor de los datos tal como vienen."""
    ax = _ejes(fig, rect)
    _estilo_ejes(ax)
    if len(datos) == 0:
        _vacio(ax, "Carga un archivo para ver sus datos")
        return
    escala = escala_valores(datos)
    xs, ys = _muestra(datos)
    ax.scatter(xs, escala.transformar(ys), s=3, color=color, alpha=0.55, linewidths=0, zorder=2)
    _titulo(ax, titulo)
    eje_posiciones(ax, len(datos), "Posición en el archivo")
    escala.aplicar(ax)
    if rect is None:
        _ajustar(fig)


# ----------------------------------------------------------------------
# Antes / despues del ordenamiento
# ----------------------------------------------------------------------
def dibujar_antes_despues(fig, original, ordenada, subtitulo="", vertical=False, rect=None):
    """Dos paneles: antes (desordenado) y despues (ordenado). La evidencia
    visual del ordenamiento es que el segundo panel forma una curva continua."""
    if rect is None:
        fig.clear()
        fig.patch.set_facecolor(FONDO)
    if len(original) == 0:
        ax = fig.add_axes(rect) if rect is not None else fig.add_subplot(111)
        _estilo_ejes(ax)
        _vacio(ax, "Ordena los datos para ver la evidencia gráfica")
        return
    if rect is not None:
        x, y, w, h = rect
        if vertical:
            ax1 = fig.add_axes([x, y + h * 0.56, w, h * 0.44])
            ax2 = fig.add_axes([x, y, w, h * 0.44])
        else:
            ax1 = fig.add_axes([x, y, w * 0.46, h])
            ax2 = fig.add_axes([x + w * 0.54, y, w * 0.46, h])
    elif vertical:
        ax1 = fig.add_subplot(2, 1, 1)
        ax2 = fig.add_subplot(2, 1, 2)
    else:
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2, sharey=ax1)
    for ax in (ax1, ax2):
        _estilo_ejes(ax)
    escala = escala_valores(ordenada, ordenada)          # la misma escala en los dos paneles
    xs, ys = _muestra(original)
    ax1.scatter(xs, escala.transformar(ys), s=3, color=NARANJA, alpha=0.55, linewidths=0, zorder=2)
    _titulo(ax1, "Antes · datos originales")
    xs, ys = _muestra(ordenada)
    ax2.plot(xs, escala.transformar(ys), color=AZUL, linewidth=2, zorder=2,
             marker="o" if len(xs) == 1 else None, markersize=4)
    _titulo(ax2, "Después · datos ordenados")
    for ax in (ax1, ax2):
        eje_posiciones(ax, len(ordenada))
        escala.aplicar(ax, "Valor" if (ax is ax1 or vertical) else "")
    if subtitulo and rect is None:
        fig.suptitle(subtitulo, fontsize=9, color=TINTA_2, x=0.01, ha="left")
    if rect is None:
        _ajustar(fig)


# ----------------------------------------------------------------------
# Comparacion de algoritmos de ordenamiento
# ----------------------------------------------------------------------
def dibujar_comparacion(fig, resultados, titulo="", rect=None):
    """Barras horizontales del tiempo de cada algoritmo.

    resultados: lista de dicts con "algoritmo", "tipo" (Interno/Externo) y
    "segundos". Se ordenan de mas rapido a mas lento con NUESTRA insercion.
    """
    from librerias.ordenamiento_interno import insercion

    ax = _ejes(fig, rect)
    _estilo_ejes(ax)
    ax.grid(True, axis="x", color=REJILLA)
    ax.grid(False, axis="y")
    if len(resultados) == 0:
        _vacio(ax, "Ejecuta la comparación para ver los tiempos")
        return

    # De mayor a menor tiempo: barh dibuja el primero abajo, asi el mas rapido queda arriba
    pares = [(r["segundos"], i) for i, r in enumerate(resultados)]
    pares, _ = insercion(pares, descendente=True)
    ordenados = [resultados[i] for _, i in pares]

    nombres = [r["algoritmo"] for r in ordenados]
    tiempos = [r["segundos"] * 1000 for r in ordenados]
    colores = [AZUL if r["tipo"] == "Interno" else NARANJA for r in ordenados]
    barras = ax.barh(nombres, tiempos, color=colores, height=0.62, edgecolor=FONDO, linewidth=2)
    mayor = 0
    for t in tiempos:
        if t > mayor:
            mayor = t
    for barra, t in zip(barras, tiempos):
        ax.text(barra.get_width() + mayor * 0.012, barra.get_y() + barra.get_height() / 2,
                _ms(t), va="center", fontsize=8, color=TINTA_2)
    ax.set_xlim(0, mayor * 1.2 if mayor > 0 else 1)
    ax.tick_params(axis="y", labelsize=9, colors=TINTA)
    ax.set_xlabel("milisegundos", fontsize=8, color=TINTA_2)
    _titulo(ax, titulo)
    tipos = []
    for r in ordenados:
        if r["tipo"] not in tipos:
            tipos.append(r["tipo"])
    if len(tipos) > 1:
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(color=AZUL, label="Interno (memoria)"),
                           Patch(color=NARANJA, label="Externo (archivos)")],
                  loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, fontsize=8, frameon=False)
    if rect is None:
        _ajustar(fig)


# ----------------------------------------------------------------------
# Comparacion de metodos de busqueda
# ----------------------------------------------------------------------
def dibujar_busquedas(fig, filas, titulo="", rect=None):
    """filas: lista de (metodo, comparaciones, segundos, apariciones)."""
    ax = _ejes(fig, rect)
    _estilo_ejes(ax)
    ax.grid(True, axis="x", color=REJILLA)
    ax.grid(False, axis="y")
    if not filas:
        _vacio(ax, "Usa «Comparar los 3» para ver esta gráfica")
        return
    nombres = [f[0] for f in filas]
    comps = [f[1] for f in filas]
    barras = ax.barh(nombres, comps, color=AZUL, height=0.5, edgecolor=FONDO, linewidth=2)
    mayor = 1
    for c in comps:
        if c > mayor:
            mayor = c
    for b, f in zip(barras, filas):
        ax.text(b.get_width() + mayor * 0.012, b.get_y() + b.get_height() / 2,
                f"{f[1]:,} comparaciones", va="center", fontsize=8, color=TINTA_2)
    ax.set_xlim(0, mayor * 1.4)
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=9, colors=TINTA)
    ax.set_xlabel("comparaciones realizadas", fontsize=8, color=TINTA_2)
    _titulo(ax, titulo)
    if rect is None:
        _ajustar(fig)


def _ms(t):
    if t >= 1000:
        return f"{t / 1000:,.2f} s"
    if t >= 10:
        return f"{t:,.0f} ms"
    return f"{t:,.2f} ms"


# ----------------------------------------------------------------------
# Laboratorio de rendimiento
# ----------------------------------------------------------------------
# Cada algoritmo tiene SIEMPRE el mismo color (el color sigue al algoritmo).
# Los externos van con linea punteada.
COLOR_ALGORITMO = {
    "Burbuja": "#e34948", "Inserción": "#eb6834", "Selección": "#eda100", "ShellSort": "#1baf7a",
    "QuickSort": "#2a78d6", "HeapSort": "#6250d6", "RadixSort": "#008300",
    "Mezcla Directa": "#e87ba4", "Mezcla Equilibrada": "#475569",
}


def dibujar_escalabilidad(fig, series, titulo="", rect=None):
    """Tiempo contra cantidad de datos en escala logaritmica (log-log): una
    recta con pendiente 2 es O(n^2); con pendiente ~1 es O(n) / O(n log n)."""
    ax = _ejes(fig, rect)
    _estilo_ejes(ax)
    if not series:
        _vacio(ax, "Ejecuta el laboratorio para ver la escalabilidad")
        return
    for s in series:
        xs = [p[0] for p in s["puntos"]]
        ys = [max(p[1], 1e-6) * 1000 for p in s["puntos"]]
        b = s["exponente"]
        etiqueta = f'{s["algoritmo"]}  (b = {b:.2f})' if b is not None else s["algoritmo"]
        ax.plot(xs, ys, color=COLOR_ALGORITMO.get(s["algoritmo"], TINTA_2), linewidth=2,
                linestyle="--" if s["tipo"] == "Externo" else "-", marker="o", markersize=4.5,
                markeredgecolor=FONDO, markeredgewidth=1, label=etiqueta)
    ax.set_xscale("log")
    ax.set_yscale("log")
    from matplotlib.ticker import FuncFormatter, NullFormatter, NullLocator
    tamanos = []
    for s in series:
        for n, _t in s["puntos"]:
            if n not in tamanos:
                tamanos.append(n)
    ax.set_xticks(tamanos)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _p: f"{int(round(x)):,}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _p: (f"{y:,.0f}" if y >= 1 else f"{y:g}")))
    ax.set_xlabel("cantidad de datos (n) · escala logarítmica", fontsize=8, color=TINTA_2)
    ax.set_ylabel("milisegundos · escala logarítmica", fontsize=8, color=TINTA_2)
    ax.grid(True, which="major", color=REJILLA)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False)
    _titulo(ax, titulo)
    if rect is None:
        _ajustar(fig)


def dibujar_matriz(fig, escenarios, nombres, matriz, rect=None):
    """Mapa de calor: filas = escenarios, columnas = algoritmos. El color es
    que tan lento fue cada algoritmo respecto al mas rapido de su fila
    (claro = rapido, oscuro = lento). El ganador de cada fila lleva borde verde."""
    ax = _ejes(fig, rect)
    if not matriz:
        _estilo_ejes(ax)
        _vacio(ax, "Ejecuta el laboratorio para ver los escenarios")
        return
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle
    mapa = LinearSegmentedColormap.from_list("azules", ["#e8f1fc", "#86b6ef", "#2a78d6", "#0d366b"])
    filas = len(matriz)
    cols = len(nombres)
    valores = []
    for fila in matriz:
        mejor = None
        for t in fila:
            if t is not None and (mejor is None or t < mejor):
                mejor = t
        renglon = []
        for t in fila:
            if t is None or mejor is None or mejor <= 0:
                renglon.append(float("nan"))
            else:
                renglon.append(min(1.0, _log10(t / mejor) / 3.0))      # 1x .. 1000x
        valores.append(renglon)
    ax.imshow(valores, cmap=mapa, vmin=0, vmax=1, aspect="auto")
    for i in range(filas):
        mejor_j = None
        for j in range(cols):
            t = matriz[i][j]
            if t is not None and (mejor_j is None or t < matriz[i][mejor_j]):
                mejor_j = j
        for j in range(cols):
            t = matriz[i][j]
            if t is None:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor="#f1f5f9", edgecolor="white",
                                       hatch="///", linewidth=0))
                ax.text(j, i, "omitido", ha="center", va="center", fontsize=7, color=TINTA_3)
                continue
            ms = t * 1000
            if t >= 10:
                texto = f"{t:,.1f} s"
            elif ms < 1:
                texto = f"{ms:.3f}"
            elif ms < 10:
                texto = f"{ms:.2f}"
            else:
                texto = f"{ms:,.1f}"
            oscuro = valores[i][j] > 0.55
            ax.text(j, i, texto, ha="center", va="center", fontsize=7.5,
                    color="white" if oscuro else TINTA, fontweight="bold" if j == mejor_j else "normal")
        if mejor_j is not None:
            ax.add_patch(Rectangle((mejor_j - 0.47, i - 0.45), 0.94, 0.9, fill=False, edgecolor=VERDE,
                                   linewidth=2.2))
    ax.set_xticks(range(cols))
    ax.set_xticklabels(nombres, rotation=30, ha="right", fontsize=8, color=TINTA)
    ax.set_yticks(range(filas))
    ax.set_yticklabels([e[0] for e in escenarios], fontsize=8.5, color=TINTA)
    ax.tick_params(length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, filas)], minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    if rect is None:
        _ajustar(fig)


def _log10(x):
    from librerias.laboratorio import ln
    return ln(x) / 2.302585092994046
