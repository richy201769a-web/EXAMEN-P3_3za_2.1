"""Pruebas de los metodos de busqueda."""

import os
import unittest

from librerias import busquedas as bq
from librerias import ordenamiento_interno as oi
from librerias import archivos as ar
from pruebas.utilidades import aleatorios, DATOS


def todas(lista, objetivo, descendente=False):
    """Busca con los 3 metodos y regresa sus posiciones."""
    sec, _ = bq.busqueda_secuencial(lista, objetivo)
    bin_, _ = bq.busqueda_binaria(lista, objetivo, descendente)
    has, _ = bq.busqueda_hash(bq.construir_tabla_hash(lista), objetivo)
    return sec, bin_, has


class Busquedas(unittest.TestCase):

    def test_lista_vacia(self):
        self.assertEqual(todas([], 5), ([], [], []))

    def test_un_elemento(self):
        self.assertEqual(todas([5], 5), ([0], [0], [0]))
        self.assertEqual(todas([5], 4), ([], [], []))

    def test_primero_ultimo_y_medio(self):
        lista = [1, 3, 5, 7, 9, 11]
        for i, v in enumerate(lista):
            with self.subTest(valor=v):
                self.assertEqual(todas(lista, v), ([i], [i], [i]))

    def test_no_encontrado_fuera_de_rango_y_entre_valores(self):
        lista = [10, 20, 30]
        for v in (-5, 0, 15, 25, 35, 10 ** 14):
            with self.subTest(valor=v):
                self.assertEqual(todas(lista, v), ([], [], []))

    def test_duplicados_regresan_todas_las_posiciones(self):
        lista = [1, 2, 2, 2, 3, 3, 9]
        self.assertEqual(todas(lista, 2), ([1, 2, 3], [1, 2, 3], [1, 2, 3]))
        self.assertEqual(todas(lista, 3), ([4, 5], [4, 5], [4, 5]))

    def test_todos_iguales(self):
        lista = [4] * 100
        sec, bin_, has = todas(lista, 4)
        self.assertEqual(len(sec), 100)
        self.assertEqual(sec, bin_)
        self.assertEqual(sec, has)

    def test_negativos(self):
        lista = [-50, -10, -10, 0, 7]
        self.assertEqual(todas(lista, -10), ([1, 2], [1, 2], [1, 2]))

    def test_orden_descendente(self):
        lista = [90, 70, 70, 40, 10, -3]
        self.assertEqual(todas(lista, 70, True), ([1, 2], [1, 2], [1, 2]))
        self.assertEqual(todas(lista, -3, True), ([5], [5], [5]))
        self.assertEqual(todas(lista, 50, True), ([], [], []))

    def test_dataset_completo_contra_secuencial(self):
        datos = ar.leer_archivo(os.path.join(DATOS, "dataset_5000_duplicados.xlsx"))["datos"]
        for desc in (False, True):
            lista, _ = oi.quick_sort(datos, desc)
            tabla = bq.construir_tabla_hash(lista)
            for objetivo in lista[::97] + [0, -1, 100001, 50000]:
                with self.subTest(valor=objetivo, descendente=desc):
                    sec, _ = bq.busqueda_secuencial(lista, objetivo)
                    self.assertEqual(bq.busqueda_binaria(lista, objetivo, desc)[0], sec)
                    self.assertEqual(bq.busqueda_hash(tabla, objetivo)[0], sec)

    def test_hash_sobre_datos_desordenados(self):
        datos = aleatorios(2000, 11)
        tabla = bq.construir_tabla_hash(datos)
        for objetivo in datos[:50]:
            self.assertEqual(bq.busqueda_hash(tabla, objetivo)[0], bq.busqueda_secuencial(datos, objetivo)[0])

    def test_hash_con_colisiones(self):
        tabla = bq.construir_tabla_hash([1, 2, 3])
        tam = tabla["tamano"]
        valores = [5, 5 + tam, 5 + 2 * tam, 5 - tam]      # todos caen en la misma cubeta
        tabla = bq.construir_tabla_hash(valores)
        tam2 = tabla["tamano"]
        valores = [5, 5 + tam2, 5 + 2 * tam2, 5 - tam2]
        tabla = bq.construir_tabla_hash(valores)
        self.assertGreaterEqual(tabla["colisiones"], 3)
        for i, v in enumerate(valores):
            self.assertEqual(bq.busqueda_hash(tabla, v)[0], [i])
        self.assertEqual(bq.busqueda_hash(tabla, 6)[0], [])

    def test_tamano_de_tabla_es_primo(self):
        for n in (0, 1, 10, 1000, 5000):
            tam = bq.construir_tabla_hash(list(range(n)))["tamano"]
            self.assertTrue(bq._es_primo(tam))
            self.assertGreaterEqual(tam, 2 * n)

    def test_eficiencia_comparaciones(self):
        lista = list(range(100000))
        _, c_sec = bq.busqueda_secuencial(lista, 99999)
        _, c_bin = bq.busqueda_binaria(lista, 99999)
        _, c_has = bq.busqueda_hash(bq.construir_tabla_hash(lista), 99999)
        self.assertEqual(c_sec, 100000)
        self.assertLessEqual(c_bin, 2 * 17 + 2)              # ~2 * log2(100000)
        self.assertLessEqual(c_has, 3)


if __name__ == "__main__":
    unittest.main()
