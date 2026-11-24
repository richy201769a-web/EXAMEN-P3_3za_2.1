"""
Pruebas de las graficas: la escala del eje de valores debe ajustarse a los
datos (normales, negativos, lejos del 0, con valores extremos, pocos datos,
todos iguales...) para que la grafica siempre se vea bien.
"""

import os
import random
import unittest

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

from librerias import archivos as ar
from librerias import exportacion as ex
from librerias import graficos as g
from librerias import ordenamiento_interno as oi
from pruebas.test_archivos import info_reporte_de_prueba
from pruebas.utilidades import DATOS, TMP, limpiar_tmp


def _con_extremo(n, semilla, minimo, maximo, extremo, posicion=None):
    rnd = random.Random(semilla)
    datos = [rnd.randint(minimo, maximo) for _ in range(n)]
    datos[posicion if posicion is not None else n // 2] = extremo
    return datos


def casos_dificiles():
    rnd = random.Random(2026)
    return {
        "negativos + 470 millones": _con_extremo(4100, 1, -50000, 50000, 470000000),
        "lejos del 0 + extremo": _con_extremo(3000, 2, 10 ** 9, 10 ** 9 + 50000, 9 * 10 ** 12),
        "extremos arriba y abajo": _con_extremo(2000, 3, -100, 100, -10 ** 10, 5) + [10 ** 10],
        "todo negativo + extremo": _con_extremo(3000, 4, -500, 0, -470000000),
        "muchos ceros + 1000": [0] * 300 + [1000] + [0] * 300,
        "5 datos con extremo": [3, 1, 4, 2, 10 ** 9],
        "dos datos": [5, 10 ** 9],
        "cola larga": [int(rnd.expovariate(1 / 1000)) for _ in range(5000)],
        "todos iguales": [42] * 100,
        "un dato": [7],
        "15 digitos +-": [rnd.choice([-1, 1]) * rnd.randint(1, 10 ** 15 - 1) for _ in range(800)],
        "normal": [rnd.randint(1, 100000) for _ in range(5000)],
    }


class EscalaDinamica(unittest.TestCase):

    def test_archivos_del_examen_usan_escala_normal(self):
        for nombre in ("dataset_1000_duplicados.txt", "dataset_5000_duplicados.xlsx", "dataset_20000_duplicados.txt"):
            with self.subTest(archivo=nombre):
                datos = ar.leer_archivo(os.path.join(DATOS, nombre))["datos"]
                self.assertFalse(g.escala_valores(datos).comprimida)
                ordenada, _ = oi.quick_sort(datos)
                self.assertFalse(g.escala_valores(ordenada, ordenada).comprimida)

    def test_detecta_valores_extremos(self):
        casos = casos_dificiles()
        for nombre in ("negativos + 470 millones", "lejos del 0 + extremo", "extremos arriba y abajo",
                       "todo negativo + extremo", "muchos ceros + 1000", "5 datos con extremo"):
            with self.subTest(caso=nombre):
                ordenada, _ = oi.quick_sort(casos[nombre])
                self.assertTrue(g.escala_valores(ordenada, ordenada).comprimida)
        for nombre in ("cola larga", "todos iguales", "un dato", "15 digitos +-", "normal"):
            with self.subTest(caso=nombre):
                ordenada, _ = oi.quick_sort(casos[nombre])
                self.assertFalse(g.escala_valores(ordenada, ordenada).comprimida)

    def test_extremos_arriba_y_abajo(self):
        ordenada, _ = oi.quick_sort(casos_dificiles()["extremos arriba y abajo"])
        e = g.escala_valores(ordenada, ordenada)
        self.assertTrue(e.arriba and e.abajo)
        self.assertTrue(-100 <= e.bajo <= e.alto <= 100)

    def test_el_grueso_de_los_datos_ocupa_la_mayor_parte(self):
        """La zona normal (lineal) debe quedarse con al menos la mitad de la altura."""
        for nombre, datos in casos_dificiles().items():
            ordenada, _ = oi.quick_sort(datos)
            e = g.escala_valores(ordenada, ordenada)
            if not e.comprimida or e.alto == e.bajo:
                continue
            with self.subTest(caso=nombre):
                total = e.t(e.maximo) - e.t(e.minimo)
                self.assertGreaterEqual((e.alto - e.bajo) / total, 0.4)

    def test_transformacion_respeta_el_orden(self):
        for nombre, datos in casos_dificiles().items():
            with self.subTest(caso=nombre):
                ordenada, _ = oi.quick_sort(datos)
                e = g.escala_valores(ordenada, ordenada)
                pos = e.transformar(ordenada)
                for i in range(len(ordenada) - 1):
                    if ordenada[i] < ordenada[i + 1]:
                        self.assertLess(pos[i], pos[i + 1])
                    else:
                        self.assertEqual(pos[i], pos[i + 1])

    def test_dentro_del_grueso_no_se_deforma(self):
        ordenada, _ = oi.quick_sort(casos_dificiles()["negativos + 470 millones"])
        e = g.escala_valores(ordenada, ordenada)
        for v in (e.bajo, 0, e.alto, (e.bajo + e.alto) // 2):
            self.assertEqual(e.t(v), v)

    def test_ascendente_y_descendente_dan_la_misma_escala(self):
        for nombre, datos in casos_dificiles().items():
            with self.subTest(caso=nombre):
                asc, _ = oi.quick_sort(datos)
                desc, _ = oi.quick_sort(datos, descendente=True)
                a = g.escala_valores(asc, asc)
                d = g.escala_valores(desc, desc)
                self.assertEqual((a.minimo, a.maximo, a.bajo, a.alto, a.arriba, a.abajo),
                                 (d.minimo, d.maximo, d.bajo, d.alto, d.arriba, d.abajo))

    def test_muestra_y_datos_completos_coinciden_en_extremos(self):
        datos = casos_dificiles()["negativos + 470 millones"] * 5          # 20,500 datos -> se usa muestra
        ordenada, _ = oi.quick_sort(datos)
        con_muestra = g.escala_valores(datos)
        completa = g.escala_valores(ordenada, ordenada)
        self.assertEqual((con_muestra.minimo, con_muestra.maximo), (completa.minimo, completa.maximo))
        self.assertEqual(con_muestra.arriba, completa.arriba)

    def test_marcas_ordenadas_sin_repetir_y_sin_encimarse(self):
        for nombre, datos in casos_dificiles().items():
            ordenada, _ = oi.quick_sort(datos)
            e = g.escala_valores(ordenada, ordenada)
            if not e.comprimida:
                continue
            with self.subTest(caso=nombre):
                marcas = e.marcas()
                self.assertGreaterEqual(len(marcas), 3)
                self.assertLessEqual(len(marcas), 12)
                etiquetas = [m for _, m in marcas]
                self.assertEqual(len(etiquetas), len(set(etiquetas)))
                total = e.t(e.maximo) - e.t(e.minimo)
                for i in range(len(marcas) - 1):
                    self.assertGreater(marcas[i + 1][0] - marcas[i][0], total * 0.02)
                for p, _ in marcas:
                    self.assertTrue(e.t(e.minimo) - total * 0.06 <= p <= e.t(e.maximo) + total * 0.06)

    def test_fuzzing_escala(self):
        """200 conjuntos al azar con formas distintas: la escala nunca falla."""
        rnd = random.Random(99)
        for k in range(200):
            n = rnd.randint(1, 400)
            centro = rnd.choice([0, 10 ** rnd.randint(1, 14), -10 ** rnd.randint(1, 14)])
            ancho = rnd.choice([0, 1, 10, 10 ** rnd.randint(1, 8)])
            datos = [centro + rnd.randint(-ancho, ancho) for _ in range(n)]
            for _ in range(rnd.randint(0, 3)):
                datos[rnd.randrange(n)] = rnd.choice([-1, 1]) * rnd.randint(0, 10 ** 15 - 1)
            with self.subTest(caso=k):
                ordenada, _ = oi.quick_sort(datos)
                e = g.escala_valores(ordenada, ordenada)
                pos = e.transformar(ordenada)
                for i in range(len(pos) - 1):
                    self.assertLessEqual(pos[i], pos[i + 1])
                if e.comprimida:
                    etiquetas = [m for _, m in e.marcas()]
                    self.assertEqual(len(etiquetas), len(set(etiquetas)))


class DibujoDeGraficas(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def _puntos_dentro(self, ax):
        y0, y1 = ax.get_ylim()
        x0, x1 = ax.get_xlim()
        for coleccion in ax.collections:
            for x, y in coleccion.get_offsets():
                self.assertTrue(y0 <= y <= y1)
                self.assertTrue(x0 <= x <= x1)
        for linea in ax.lines:
            if linea.get_linestyle() == "-":
                for y in linea.get_ydata():
                    self.assertTrue(y0 <= y <= y1)

    def test_todas_las_graficas_con_casos_dificiles(self):
        for nombre, datos in casos_dificiles().items():
            asc, _ = oi.quick_sort(datos)
            desc, _ = oi.quick_sort(datos, descendente=True)
            with self.subTest(caso=nombre):
                fig = Figure(figsize=(6, 3))
                g.dibujar_datos(fig, datos)
                self._puntos_dentro(fig.axes[0])
                for orden in (asc, desc):
                    for vertical in (False, True):
                        fig = Figure(figsize=(6, 3))
                        g.dibujar_antes_despues(fig, datos, orden, vertical=vertical)
                        for ax in fig.axes:
                            self._puntos_dentro(ax)
                        fig.savefig(os.path.join(TMP, "grafica.png"))

    def test_el_valor_extremo_siempre_se_dibuja(self):
        datos = casos_dificiles()["negativos + 470 millones"] * 5          # mas de 6,000: se dibuja una muestra
        fig = Figure(figsize=(6, 3))
        g.dibujar_datos(fig, datos)
        ys = [y for _x, y in fig.axes[0].collections[0].get_offsets()]
        e = g.escala_valores(datos)
        self.assertIn(e.t(470000000), ys)
        self.assertIn(e.t(e.minimo), ys)

    def test_etiqueta_avisa_cuando_la_escala_cambia(self):
        fig = Figure(figsize=(6, 3))
        g.dibujar_datos(fig, casos_dificiles()["negativos + 470 millones"])
        self.assertIn("extremos", fig.axes[0].get_ylabel())
        fig = Figure(figsize=(6, 3))
        g.dibujar_datos(fig, casos_dificiles()["normal"])
        self.assertEqual(fig.axes[0].get_ylabel(), "Valor")

    def test_un_solo_dato_no_repite_marcas(self):
        fig = Figure(figsize=(6, 3))
        g.dibujar_antes_despues(fig, [7], [7])
        fig.canvas.draw() if hasattr(fig.canvas, "draw") else None
        x0, x1 = fig.axes[0].get_xlim()
        self.assertLess(x0, 1)
        self.assertGreater(x1, 1)
        self.assertEqual(list(fig.axes[0].get_xticks()), [1])

    def test_reporte_pdf_con_valores_extremos(self):
        for nombre in ("negativos + 470 millones", "lejos del 0 + extremo", "un dato", "todos iguales"):
            with self.subTest(caso=nombre):
                datos = casos_dificiles()[nombre]
                ordenada, _ = oi.quick_sort(datos)
                info = info_reporte_de_prueba()
                info["original"] = datos
                info["resultado"]["lista"] = ordenada
                info["resultado"]["n"] = len(datos)
                ruta = os.path.join(TMP, "reporte_extremos.pdf")
                ex.reporte_final(ruta, info)
                with open(ruta, "rb") as f:
                    self.assertEqual(f.read(4), b"%PDF")


def _etiquetas_y(ax):
    return [t.get_text() for t in ax.get_yticklabels()]


def _con_tamano(n, semilla=5, extremo=None):
    rnd = random.Random(semilla)
    datos = [rnd.randint(-50000, 99999) for _ in range(n)]
    if extremo is not None and n > 2:
        datos[n // 3] = extremo
    return datos


class EjesSegunLosDatos(unittest.TestCase):
    """Los ejes se ajustan a los datos procesados: X de 1 al total y Y del
    menor al mayor valor real, sin importar cuantos datos sean."""

    TAMANOS = (1, 2, 7, 100, 4100, 5000, 20000, 60000, 250000)

    def _revisar_ejes(self, ax, datos, escala):
        n = len(datos)
        menor = mayor = datos[0]
        for v in datos:
            if v < menor:
                menor = v
            if v > mayor:
                mayor = v
        xt = list(ax.get_xticks())
        self.assertEqual(xt[0], 1)
        self.assertEqual(xt[-1], n)                          # la ultima marca es el total
        x0, x1 = ax.get_xlim()
        self.assertTrue(x0 < 1 and x1 > n - 0.5)
        self.assertLessEqual(x1 - n, max(n * 0.02, 1))       # sin espacio de sobra
        etiquetas = _etiquetas_y(ax)
        self.assertEqual(etiquetas[0], f"{menor:,}")         # primera marca: el menor real
        self.assertEqual(etiquetas[-1], f"{mayor:,}")        # ultima marca: el mayor real
        y0, y1 = ax.get_ylim()
        self.assertTrue(y0 <= escala.t(menor) and escala.t(mayor) <= y1)
        alto = escala.t(mayor) - escala.t(menor)
        if alto > 0:
            self.assertLessEqual(y1 - escala.t(mayor), alto * 0.06)    # sin espacio de sobra arriba
            self.assertLessEqual(escala.t(menor) - y0, alto * 0.06)

    def test_dibujar_datos_con_cualquier_tamano(self):
        for n in self.TAMANOS:
            for extremo in (None, 470000000):
                with self.subTest(n=n, extremo=extremo):
                    datos = _con_tamano(n, extremo=extremo)
                    fig = Figure(figsize=(6, 3))
                    g.dibujar_datos(fig, datos)
                    ax = fig.axes[0]
                    self._revisar_ejes(ax, datos, g.escala_valores(datos))
                    xs = [x for x, _y in ax.collections[0].get_offsets()]
                    self.assertEqual(min(xs), 1)
                    self.assertEqual(max(xs), n)             # se dibuja hasta el ultimo dato

    def test_antes_y_despues_con_cualquier_tamano(self):
        from librerias.ordenamiento_interno import radix_sort
        for n in self.TAMANOS:
            for desc in (False, True):
                with self.subTest(n=n, descendente=desc):
                    datos = _con_tamano(n, semilla=n, extremo=10 ** 12 if n % 2 else None)
                    ordenada, _ = radix_sort(datos, descendente=desc)
                    escala = g.escala_valores(ordenada, ordenada)
                    for vertical in (False, True):
                        fig = Figure(figsize=(6, 3))
                        g.dibujar_antes_despues(fig, datos, ordenada, vertical=vertical)
                        for ax in fig.axes:
                            self._revisar_ejes(ax, datos, escala)

    def test_hasta_40000_se_dibujan_todos_los_puntos(self):
        for n in (4100, 5000, 20000, 40000):
            with self.subTest(n=n):
                datos = _con_tamano(n)
                fig = Figure(figsize=(6, 3))
                g.dibujar_datos(fig, datos)
                self.assertEqual(len(fig.axes[0].collections[0].get_offsets()), n)

    def test_archivos_grandes_no_pierden_extremos(self):
        datos = _con_tamano(250000, semilla=9)
        datos[123457] = -10 ** 14
        datos[200001] = 10 ** 14
        xs, ys = g._muestra(datos)
        self.assertLessEqual(len(xs), g.MAX_PUNTOS + 2)
        self.assertEqual((xs[0], xs[-1]), (1, 250000))
        self.assertIn(-10 ** 14, ys)
        self.assertIn(10 ** 14, ys)
        for i in range(len(xs) - 1):
            self.assertLess(xs[i], xs[i + 1])                 # posiciones en orden y sin repetir
        for x, y in zip(xs, ys):
            self.assertEqual(datos[x - 1], y)                 # cada punto es un dato real

    def test_curva_ordenada_grande_sigue_ordenada(self):
        from librerias.ordenamiento_interno import radix_sort
        ordenada, _ = radix_sort(_con_tamano(250000, semilla=3))
        _xs, ys = g._muestra(ordenada)
        for i in range(len(ys) - 1):
            self.assertLessEqual(ys[i], ys[i + 1])

    def test_paneles_del_reporte_pdf(self):
        from librerias.ordenamiento_interno import radix_sort
        for n in (1, 4100, 60000):
            with self.subTest(n=n):
                datos = _con_tamano(n, extremo=470000000)
                ordenada, _ = radix_sort(datos)
                info = info_reporte_de_prueba()
                info["original"] = datos
                info["resultado"]["lista"] = ordenada
                escala = g.escala_valores(ordenada, ordenada)
                for panel in (ex._panel_antes, ex._panel_despues):
                    fig = Figure(figsize=(8.5, 11))
                    panel(fig, [0.1, 0.1, 0.8, 0.3], info)
                    self._revisar_ejes(fig.axes[0], datos, escala)


if __name__ == "__main__":
    unittest.main()
