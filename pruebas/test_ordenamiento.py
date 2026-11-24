"""Pruebas de los ordenamientos internos y externos."""

import os
import unittest

from librerias import ordenamiento_interno as oi
from librerias import ordenamiento_externo as oe
from librerias import archivos as ar
from pruebas.utilidades import conteo, aleatorios, DATOS, TMP, limpiar_tmp

CASOS_BORDE = {
    "vacía": [],
    "un elemento": [7],
    "dos desordenados": [2, 1],
    "dos iguales": [4, 4],
    "todos iguales": [5] * 50,
    "ya ordenada": list(range(100)),
    "orden inverso": list(range(100, 0, -1)),
    "negativos y cero": [0, -5, 3, -1, 0, 8, -100, 2],
    "extremos": [10 ** 15 - 1, -(10 ** 15 - 1), 0, 1, -1],
    "muchos duplicados": [3, 1, 3, 1, 2, 2, 3, 1, 2] * 20,
    "aleatoria": aleatorios(800, 1),
    "aleatoria grande": aleatorios(3000, 2, -50000, 50000),
}


class OrdenamientoInterno(unittest.TestCase):

    def comprobar(self, funcion, datos, descendente):
        copia = list(datos)
        resultado, est = funcion(datos, descendente)
        self.assertEqual(datos, copia, "el algoritmo modificó la lista original")
        self.assertEqual(len(resultado), len(datos))
        self.assertTrue(oi.esta_ordenada(resultado, descendente))
        self.assertEqual(conteo(resultado), conteo(datos), "se perdieron o duplicaron valores")
        self.assertIn("comparaciones", est)
        self.assertIn("movimientos", est)

    def test_casos_borde_todos_los_algoritmos(self):
        for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
            for caso, datos in CASOS_BORDE.items():
                for desc in (False, True):
                    with self.subTest(algoritmo=nombre, caso=caso, descendente=desc):
                        self.comprobar(funcion, datos, desc)

    def test_datasets_del_profesor(self):
        for archivo in ("dataset_1000_duplicados.txt", "dataset_5000_duplicados.xlsx"):
            datos = ar.leer_archivo(os.path.join(DATOS, archivo))["datos"]
            for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
                for desc in (False, True):
                    with self.subTest(archivo=archivo, algoritmo=nombre, descendente=desc):
                        self.comprobar(funcion, datos, desc)

    def test_estres_20000_metodos_rapidos(self):
        datos = ar.leer_archivo(os.path.join(DATOS, "dataset_20000_duplicados.txt"))["datos"]
        self.assertEqual(len(datos), 20000)
        for nombre in ("ShellSort", "QuickSort", "HeapSort", "RadixSort"):
            for desc in (False, True):
                with self.subTest(algoritmo=nombre, descendente=desc):
                    self.comprobar(oi.ALGORITMOS_INTERNOS[nombre], datos, desc)

    def test_todos_dan_el_mismo_resultado(self):
        datos = aleatorios(1500, 9)
        referencia, _ = oi.insercion(datos)
        for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
            with self.subTest(algoritmo=nombre):
                self.assertEqual(funcion(datos)[0], referencia)

    def test_burbuja_se_detiene_si_ya_esta_ordenada(self):
        _, est = oi.burbuja(list(range(1000)))
        self.assertEqual(est["comparaciones"], 999)          # una sola pasada

    def test_progreso_y_cancelacion(self):
        class Alto(Exception):
            pass
        llamadas = []

        def progreso(hechos, total):
            llamadas.append((hechos, total))
            if len(llamadas) == 3:
                raise Alto()
        for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
            llamadas.clear()
            with self.subTest(algoritmo=nombre):
                try:
                    funcion(aleatorios(3000, 4), False, progreso)
                except Alto:
                    pass
                self.assertGreater(len(llamadas), 0)

    def test_esta_ordenada(self):
        self.assertTrue(oi.esta_ordenada([]))
        self.assertTrue(oi.esta_ordenada([1, 1, 2]))
        self.assertFalse(oi.esta_ordenada([2, 1]))
        self.assertTrue(oi.esta_ordenada([3, 3, 1], True))
        self.assertFalse(oi.esta_ordenada([1, 3], True))


class OrdenamientoExterno(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def test_casos_borde(self):
        for nombre in oe.ALGORITMOS_EXTERNOS:
            for caso, datos in CASOS_BORDE.items():
                for desc in (False, True):
                    with self.subTest(algoritmo=nombre, caso=caso, descendente=desc):
                        resultado, est = oe.ordenar_externo(datos, nombre, TMP, desc)
                        self.assertTrue(oi.esta_ordenada(resultado, desc))
                        self.assertEqual(conteo(resultado), conteo(datos))

    def test_datasets(self):
        for archivo in ("dataset_1000_duplicados.txt", "dataset_5000_duplicados.xlsx",
                        "dataset_20000_duplicados.txt"):
            datos = ar.leer_archivo(os.path.join(DATOS, archivo))["datos"]
            for nombre in oe.ALGORITMOS_EXTERNOS:
                for desc in (False, True):
                    with self.subTest(archivo=archivo, algoritmo=nombre, descendente=desc):
                        resultado, _ = oe.ordenar_externo(datos, nombre, TMP, desc)
                        self.assertTrue(oi.esta_ordenada(resultado, desc))
                        self.assertEqual(conteo(resultado), conteo(datos))

    def test_no_quedan_archivos_temporales(self):
        oe.ordenar_externo(aleatorios(500, 3), "Mezcla Directa", TMP)
        oe.ordenar_externo(aleatorios(500, 3), "Mezcla Equilibrada", TMP)
        self.assertEqual(os.listdir(TMP), [])

    def test_temporales_se_borran_al_cancelar(self):
        class Alto(Exception):
            pass

        def progreso(hechos, total):
            raise Alto()
        for nombre in oe.ALGORITMOS_EXTERNOS:
            with self.subTest(algoritmo=nombre):
                with self.assertRaises(Alto):
                    oe.ordenar_externo(aleatorios(10000, 5), nombre, TMP, False, progreso)
                self.assertEqual(os.listdir(TMP), [])

    def test_mezcla_equilibrada_aprovecha_tramos(self):
        ruta = os.path.join(TMP, "F.txt")
        oe.escribir_lista(ruta, list(range(1000)))           # ya ordenado: 1 tramo
        est = oe.mezcla_equilibrada(ruta, TMP)
        self.assertEqual(est["tramos_iniciales"], 1)
        self.assertEqual(est["pasadas"], 0)
        oe.escribir_lista(ruta, list(range(1000)))
        est_directa = oe.mezcla_directa(ruta, TMP)
        self.assertEqual(est_directa["pasadas"], 10)          # techo(log2 1000)

    def test_metodo_desconocido(self):
        with self.assertRaises(oe.ErrorOrdenExterno):
            oe.ordenar_externo([3, 1], "Inventado", TMP)

    def test_intercalacion(self):
        a = os.path.join(TMP, "A.txt")
        b = os.path.join(TMP, "B.txt")
        c = os.path.join(TMP, "C.txt")
        oe.escribir_lista(a, [1, 4, 4, 9])
        oe.escribir_lista(b, [2, 3, 4, 10, 11])
        est = oe.intercalar_archivos(a, b, c)
        self.assertEqual(oe.leer_lista(c), [1, 2, 3, 4, 4, 4, 9, 10, 11])
        self.assertGreater(est["comparaciones"], 0)
        # descendente
        oe.escribir_lista(a, [9, 5, 1])
        oe.escribir_lista(b, [8, 2])
        oe.intercalar_archivos(a, b, c, descendente=True)
        self.assertEqual(oe.leer_lista(c), [9, 8, 5, 2, 1])
        # un archivo vacio
        oe.escribir_lista(a, [])
        oe.escribir_lista(b, [1, 2])
        oe.intercalar_archivos(a, b, c)
        self.assertEqual(oe.leer_lista(c), [1, 2])

    def test_intercalacion_rechaza_archivo_desordenado(self):
        a = os.path.join(TMP, "A.txt")
        b = os.path.join(TMP, "B.txt")
        oe.escribir_lista(a, [1, 5, 3])
        oe.escribir_lista(b, [2, 4])
        with self.assertRaises(oe.ErrorOrdenExterno) as ctx:
            oe.intercalar_archivos(a, b, os.path.join(TMP, "C.txt"))
        self.assertIn("A", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
