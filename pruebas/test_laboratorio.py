"""Pruebas del Laboratorio de rendimiento."""

import math
import os
import unittest

from librerias import laboratorio as lab
from librerias import ordenamiento_interno as oi
from librerias import archivos as ar
from librerias import exportacion as ex
from pruebas.utilidades import conteo, aleatorios, DATOS, TMP, limpiar_tmp


class MatematicasPropias(unittest.TestCase):

    def test_logaritmo_propio_igual_a_math(self):
        for x in (1e-9, 0.001, 0.5, 1, 1.5, 2, 3.7, 10, 1234.5, 1e9, 7.3e15):
            self.assertAlmostEqual(lab.ln(x), math.log(x), places=10)

    def test_logaritmo_invalido(self):
        for x in (0, -1):
            with self.assertRaises(ValueError):
                lab.ln(x)

    def test_exponente_de_crecimiento(self):
        cuadratico = [(n, (n / 1000) ** 2) for n in (500, 1000, 2000, 4000)]
        lineal = [(n, n / 1e5) for n in (500, 1000, 2000, 4000)]
        self.assertAlmostEqual(lab.exponente_crecimiento(cuadratico), 2.0, places=6)
        self.assertAlmostEqual(lab.exponente_crecimiento(lineal), 1.0, places=6)
        self.assertIsNone(lab.exponente_crecimiento([(100, 0.5)]))
        self.assertIsNone(lab.exponente_crecimiento([(100, 0.0), (200, 0.0)]))

    def test_interpretacion(self):
        self.assertIn("cuadrático", lab.interpretar_exponente(2.01))
        self.assertIn("n log n", lab.interpretar_exponente(1.1))
        self.assertIn("n^1.5", lab.interpretar_exponente(1.5))
        self.assertIn("lineal", lab.interpretar_exponente(0.9))
        self.assertIn("Sin datos", lab.interpretar_exponente(None))

    def test_generador_propio_es_reproducible_y_en_rango(self):
        a, b = lab.generador(5), lab.generador(5)
        serie_a = [a(100) for _ in range(500)]
        self.assertEqual(serie_a, [b(100) for _ in range(500)])
        self.assertTrue(all(0 <= v < 100 for v in serie_a))
        self.assertGreater(len(conteo(serie_a)), 80)          # no es constante


class Escenarios(unittest.TestCase):

    def setUp(self):
        self.datos = ar.leer_archivo(os.path.join(DATOS, "dataset_1000_duplicados.txt"))["datos"]

    def test_escenarios_conservan_los_datos(self):
        escenarios = lab.generar_escenarios(self.datos)
        nombres = [e[0] for e in escenarios]
        self.assertEqual(nombres, ["Datos pequeños", "Datos masivos", "Datos parcialmente ordenados",
                                   "Orden inverso", "Muchos duplicados"])
        _t, _d, masivos = escenarios[1]
        _t, _d, casi = escenarios[2]
        _t, _d, inverso = escenarios[3]
        _t, _d, dup = escenarios[4]
        self.assertEqual(conteo(casi), conteo(self.datos))
        self.assertEqual(conteo(inverso), conteo(self.datos))
        self.assertTrue(oi.esta_ordenada(inverso, descendente=True))
        self.assertFalse(oi.esta_ordenada(casi))
        self.assertLessEqual(len(conteo(dup)), 50)
        self.assertEqual(masivos, self.datos)

    def test_casi_ordenado_cada_dato_cerca_de_su_lugar(self):
        _t, _d, casi = lab.generar_escenarios(self.datos)[2]
        ordenada, _ = oi.quick_sort(casi)
        desorden = 0
        for i in range(len(casi)):
            if casi[i] != ordenada[i]:
                desorden += 1
        self.assertLess(desorden, len(casi) * 0.15)

    def test_matriz_y_recomendacion(self):
        limpiar_tmp()
        nombres = ["Inserción", "ShellSort", "QuickSort", "RadixSort", "Mezcla Directa", "Mezcla Equilibrada"]
        escenarios, matriz = lab.matriz_escenarios(self.datos, nombres, TMP)
        self.assertEqual(len(matriz), 5)
        self.assertTrue(all(len(f) == len(nombres) for f in matriz))
        self.assertTrue(all(t is not None and t >= 0 for f in matriz for t in f))
        busquedas = lab.busquedas_frecuentes(self.datos, muestra=40)
        self.assertEqual([b["metodo"] for b in busquedas], ["Secuencial", "Binaria", "Hash"])
        teoricas = {"Datos pequeños": "Inserción / ShellSort", "Datos masivos": "QuickSort / RadixSort",
                    "Archivos externos": "Mezcla Equilibrada", "Datos parcialmente ordenados": "Inserción",
                    "Búsquedas frecuentes": "Hash"}
        filas = lab.recomendacion_empirica(nombres, escenarios, matriz, busquedas, teoricas)
        self.assertEqual(len(filas), 5)
        externo = [f for f in filas if f["escenario"] == "Archivos externos"][0]
        self.assertIn(externo["ganador"], ("Mezcla Directa", "Mezcla Equilibrada"))
        self.assertEqual(os.listdir(TMP), [])

    def test_cuadraticos_omitidos_en_datos_grandes_salvo_adaptativos(self):
        datos = aleatorios(lab.MAX_CUADRATICO + 10, 3, 0, 10 ** 6)
        _esc, matriz = lab.matriz_escenarios(datos, ["Selección", "Inserción", "RadixSort"], TMP)
        masivos, casi = matriz[1], matriz[2]
        self.assertIsNone(masivos[0])               # Selección omitida (O(n²) con muchos datos)
        self.assertIsNone(masivos[1])
        self.assertIsNone(casi[0])                  # Selección nunca es adaptativo
        self.assertIsNotNone(casi[1])               # Inserción sí se mide con datos casi ordenados
        self.assertIsNotNone(masivos[2])

    def test_escalabilidad_respeta_presupuesto(self):
        original = lab.PRESUPUESTO
        try:
            lab.PRESUPUESTO = 0.0                    # cualquier medicion lo supera: un solo tamano
            series = lab.escalabilidad(self.datos, ["QuickSort"], TMP)
            self.assertEqual(len(series[0]["puntos"]), 1)
        finally:
            lab.PRESUPUESTO = original
        series = lab.escalabilidad(self.datos, ["QuickSort", "RadixSort"], TMP)
        for s in series:
            self.assertEqual(s["puntos"][-1][0], len(self.datos))

    def test_cancelacion(self):
        class Alto(Exception):
            pass

        def progreso(h, t):
            raise Alto()
        with self.assertRaises(Alto):
            lab.escalabilidad(self.datos, ["Inserción"], TMP, progreso)


class ReporteConLaboratorio(unittest.TestCase):

    def test_reporte_final_con_laboratorio(self):
        from pruebas.test_archivos import info_reporte_de_prueba
        limpiar_tmp()
        datos = aleatorios(600, 8, 0, 10000)
        nombres = ["Inserción", "QuickSort", "Mezcla Directa", "Mezcla Equilibrada"]
        series = lab.escalabilidad(datos, nombres, TMP)
        escenarios, matriz = lab.matriz_escenarios(datos, nombres, TMP)
        busquedas = lab.busquedas_frecuentes(datos, muestra=20)
        rec = lab.recomendacion_empirica(nombres, escenarios, matriz, busquedas, {})
        info = info_reporte_de_prueba()
        info["laboratorio"] = {"series": series, "escenarios": escenarios, "matriz": matriz, "nombres": nombres,
                               "busquedas": busquedas, "recomendaciones": rec, "n": len(datos)}
        ruta = os.path.join(TMP, "reporte_lab.pdf")
        ex.reporte_final(ruta, info)
        with open(ruta, "rb") as f:
            contenido = f.read()
        self.assertEqual(contenido.count(b"/Type /Page") - contenido.count(b"/Type /Pages"), 9)


if __name__ == "__main__":
    unittest.main()
