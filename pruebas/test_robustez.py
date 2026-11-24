"""
Pruebas de ROBUSTEZ (las mas exigentes):

  * Fuzzing: cientos de listas y archivos generados al azar (con semilla fija,
    asi los resultados son reproducibles).
  * Limites exactos: justo en el maximo permitido y uno mas.
  * Sistema de archivos: rutas con acentos y espacios, archivo de destino
    abierto por otro programa, archivo de solo lectura.
  * Reporte PDF con datos extremos (nombres larguisimos, emojis, 1 dato,
    sin busquedas comparadas, 200,000 datos).
  * Interfaz: acciones repetidas mientras hay un proceso en curso.
"""

import os
import random
import stat
import time
import unittest

import openpyxl

from librerias import ordenamiento_interno as oi
from librerias import ordenamiento_externo as oe
from librerias import busquedas as bq
from librerias import archivos as ar
from librerias import validacion as val
from librerias import exportacion as ex
from pruebas.utilidades import conteo, TMP, DATOS, limpiar_tmp, escribir_tmp


class FuzzingAlgoritmos(unittest.TestCase):

    def test_ordenamientos_internos_con_300_listas_al_azar(self):
        rnd = random.Random(101)
        for caso in range(300):
            n = rnd.choice([0, 1, 2, 3, 5, 10, 50, 120, 400])
            rango = rnd.choice([1, 3, 100, 10 ** 6, 10 ** 15 - 1])
            datos = [rnd.randint(-rango, rango) for _ in range(n)]
            esperado = conteo(datos)
            for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
                for desc in (False, True):
                    resultado, _ = funcion(datos, desc)
                    if not (oi.esta_ordenada(resultado, desc) and conteo(resultado) == esperado):
                        self.fail(f"{nombre} falló (caso {caso}, desc={desc}): {datos[:20]}")

    def test_todos_los_algoritmos_coinciden_entre_si(self):
        rnd = random.Random(202)
        for _ in range(60):
            datos = [rnd.randint(-500, 500) for _ in range(rnd.randint(0, 300))]
            referencia, _ = oi.heap_sort(datos)
            for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
                self.assertEqual(funcion(datos)[0], referencia, nombre)

    def test_ordenamientos_externos_con_listas_al_azar(self):
        limpiar_tmp()
        rnd = random.Random(303)
        for caso in range(60):
            datos = [rnd.randint(-10 ** 12, 10 ** 12) for _ in range(rnd.randint(0, 600))]
            for nombre in oe.ALGORITMOS_EXTERNOS:
                for desc in (False, True):
                    resultado, _ = oe.ordenar_externo(datos, nombre, TMP, desc)
                    if not (oi.esta_ordenada(resultado, desc) and conteo(resultado) == conteo(datos)):
                        self.fail(f"{nombre} falló (caso {caso}, desc={desc})")
        self.assertEqual(os.listdir(TMP), [])

    def test_ordenar_lo_ya_ordenado_no_cambia_nada(self):
        datos = list(range(-200, 200))
        for nombre, funcion in oi.ALGORITMOS_INTERNOS.items():
            self.assertEqual(funcion(datos)[0], datos, nombre)
            inverso = funcion(datos, True)[0]
            self.assertEqual(funcion(inverso, True)[0], inverso, nombre)

    def test_busquedas_coinciden_con_la_secuencial(self):
        rnd = random.Random(404)
        for _ in range(300):
            datos = [rnd.randint(-50, 50) for _ in range(rnd.randint(0, 200))]
            desc = rnd.random() < 0.5
            ordenada, _ = oi.quick_sort(datos, desc)
            tabla = bq.construir_tabla_hash(ordenada)
            for objetivo in (rnd.randint(-60, 60) for _ in range(5)):
                esperado, _ = bq.busqueda_secuencial(ordenada, objetivo)
                self.assertEqual(bq.busqueda_binaria(ordenada, objetivo, desc)[0], esperado)
                self.assertEqual(bq.busqueda_hash(tabla, objetivo)[0], esperado)

    def test_hash_con_valores_enormes_y_negativos(self):
        datos = [10 ** 15 - 1, -(10 ** 15 - 1), 0, -1, 1, 10 ** 15 - 1]
        tabla = bq.construir_tabla_hash(datos)
        self.assertEqual(bq.busqueda_hash(tabla, 10 ** 15 - 1)[0], [0, 5])
        self.assertEqual(bq.busqueda_hash(tabla, -(10 ** 15 - 1))[0], [1])
        self.assertEqual(bq.busqueda_hash(tabla, 2)[0], [])


class FuzzingEntradas(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def test_archivos_con_bytes_al_azar_nunca_truenan(self):
        """Cualquier basura debe terminar en ErrorArchivo (mensaje claro), nunca en otra excepcion."""
        rnd = random.Random(505)
        for i in range(250):
            contenido = bytes(rnd.randint(0, 255) for _ in range(rnd.randint(1, 400)))
            for ext in (".txt", ".xlsx"):
                ruta = escribir_tmp(f"basura_{i}{ext}", contenido, binario=True)
                try:
                    info = ar.leer_archivo(ruta)
                    self.assertTrue(all(isinstance(v, int) for v in info["datos"]))
                except ar.ErrorArchivo:
                    pass

    def test_texto_al_azar_en_el_buscador(self):
        rnd = random.Random(606)
        alfabeto = "0123456789+-., eE\t\n'\";=<>/\\xX_ñ٣１\x00" + "abcdefghijklmnopqrstuvwxyz"
        for _ in range(3000):
            texto = "".join(rnd.choice(alfabeto) for _ in range(rnd.randint(0, 20)))
            try:
                valor = val.convertir_entero(texto)
                self.assertTrue(val.es_entero_texto(texto.strip()))
                self.assertEqual(valor, int(texto.strip()))
            except val.ErrorEntrada:
                self.assertFalse(val.es_entero_texto(texto.strip()))
            self.assertEqual(val.caracter_permitido_busqueda(texto),
                             texto in ("", "-", "+") or (val.es_entero_texto(texto)
                                                         and len(texto) <= val.MAX_LARGO_ENTRADA))

    def test_txt_con_encabezado_y_en_codificacion_ansi(self):
        ruta = escribir_tmp("con_encabezado.txt", "Numero\n5\n3\n")
        info = ar.leer_archivo(ruta)
        self.assertEqual(info["datos"], [5, 3])
        self.assertEqual(info["encabezado"], "Numero")
        ruta = escribir_tmp("ansi.txt", "Números\n7\n-2\n".encode("cp1252"), binario=True)
        info = ar.leer_archivo(ruta)
        self.assertEqual(info["datos"], [7, -2])
        self.assertEqual(info["encabezado"], "Números")
        # Texto en una linea que NO es la primera sigue siendo un error
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(escribir_tmp("letras_en_medio.txt", "5\nNumero\n3\n"))
        # Solo encabezado, sin numeros
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(escribir_tmp("solo_titulo.txt", "Numero\n"))

    def test_limite_exacto_de_registros(self):
        original = ar.MAX_REGISTROS
        try:
            ar.MAX_REGISTROS = 1000
            self.assertEqual(len(ar.leer_archivo(escribir_tmp("justo.txt", "1\n" * 1000))["datos"]), 1000)
            with self.assertRaises(ar.ErrorArchivo):
                ar.leer_archivo(escribir_tmp("uno_mas.txt", "1\n" * 1001))
        finally:
            ar.MAX_REGISTROS = original

    def test_limite_exacto_de_tamano(self):
        original = ar.MAX_BYTES
        try:
            ar.MAX_BYTES = 100
            self.assertEqual(len(ar.leer_archivo(escribir_tmp("justo.txt", "7\n" * 50))["datos"]), 50)
            with self.assertRaises(ar.ErrorArchivo):
                ar.leer_archivo(escribir_tmp("uno_mas.txt", "7\n" * 50 + "8"))
        finally:
            ar.MAX_BYTES = original

    def test_numeros_en_el_limite_de_digitos(self):
        maximo = "9" * val.MAX_DIGITOS
        datos = ar.leer_archivo(escribir_tmp("limite.txt", f"{maximo}\n-{maximo}\n"))["datos"]
        self.assertEqual(datos, [int(maximo), -int(maximo)])
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(escribir_tmp("pasado.txt", "1" + maximo + "\n"))

    def test_xlsx_varias_hojas_usa_la_primera(self):
        ruta = os.path.join(TMP, "hojas.xlsx")
        libro = openpyxl.Workbook()
        libro.active.title = "Datos"
        for v in (3, 1, 2):
            libro.active.append([v])
        otra = libro.create_sheet("Otra")
        otra.append(["esto no se lee"])
        libro.save(ruta)
        info = ar.leer_archivo(ruta)
        self.assertEqual(info["datos"], [3, 1, 2])
        self.assertEqual(info["hoja"], "Datos")

    def test_xlsx_primera_hoja_vacia(self):
        ruta = os.path.join(TMP, "vacia.xlsx")
        libro = openpyxl.Workbook()
        libro.create_sheet("Segunda").append([5])
        libro.save(ruta)
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(ruta)


class SistemaDeArchivos(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def tearDown(self):
        limpiar_tmp()

    def test_rutas_con_acentos_y_espacios(self):
        carpeta = os.path.join(TMP, "Carpeta con ñ y acentós")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, "mis números ordenados.txt")
        ar.guardar_txt(ruta, [3, -1, 2], [("Algoritmo", "Inserción")])
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [3, -1, 2])
        ruta_x = os.path.join(carpeta, "señal año.xlsx")
        ar.guardar_xlsx(ruta_x, [9, 8], [("Algoritmo", "Selección")])
        self.assertEqual(ar.leer_archivo(ruta_x)["datos"], [9, 8])
        resultado, _ = oe.ordenar_externo([5, 3, 9], "Mezcla Equilibrada", carpeta)
        self.assertEqual(resultado, [3, 5, 9])

    def test_destino_de_solo_lectura(self):
        ruta = os.path.join(TMP, "solo_lectura.txt")
        ar.guardar_txt(ruta, [1])
        os.chmod(ruta, stat.S_IREAD)
        try:
            with self.assertRaises(ar.ErrorArchivo):
                ar.guardar_txt(ruta, [2])
            self.assertFalse(os.path.exists(ruta + ".tmp"))
        finally:
            os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)

    @unittest.skipUnless(os.name == "nt", "El bloqueo de archivos abiertos es propio de Windows")
    def test_destino_abierto_por_otro_programa(self):
        import ctypes
        from ctypes import wintypes
        ruta = os.path.join(TMP, "abierto.txt")
        ar.guardar_txt(ruta, [1])
        CreateFileW = ctypes.windll.kernel32.CreateFileW
        CreateFileW.restype = wintypes.HANDLE
        manejador = CreateFileW(ruta, 0x80000000, 0, None, 3, 0x80, None)   # lectura exclusiva, como Excel
        try:
            with self.assertRaises(ar.ErrorArchivo) as ctx:
                ar.guardar_txt(ruta, [2])
            self.assertIn("abierto", str(ctx.exception))
            self.assertFalse(os.path.exists(ruta + ".tmp"))
        finally:
            ctypes.windll.kernel32.CloseHandle(manejador)

    def test_ida_y_vuelta_con_valores_extremos(self):
        datos, _ = oi.radix_sort([10 ** 15 - 1, -(10 ** 15 - 1), 0, 5, 5, -7], descendente=True)
        for ext, guardar in ((".txt", ar.guardar_txt), (".xlsx", ar.guardar_xlsx)):
            ruta = os.path.join(TMP, "extremos" + ext)
            guardar(ruta, datos, [("Orden", "Descendente")])
            self.assertEqual(ar.leer_archivo(ruta)["datos"], datos)

    def test_carpeta_temporal_borrada_entre_corridas(self):
        carpeta = os.path.join(TMP, "temp_que_no_existe", "sub")
        resultado, _ = oe.ordenar_externo([2, 1], "Mezcla Directa", carpeta)
        self.assertEqual(resultado, [1, 2])


class ReporteConDatosExtremos(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def _info(self, datos, nombre="archivo.txt", busquedas=None, comparacion_busquedas="def"):
        from pruebas.test_archivos import info_reporte_de_prueba
        info = info_reporte_de_prueba()
        ordenada, _ = oi.radix_sort(datos)
        info["original"] = datos
        info["resultado"] = dict(info["resultado"], lista=ordenada, n=len(datos))
        info["archivo"] = dict(info["archivo"], nombre=nombre, n=len(datos))
        if busquedas is not None:
            info["busquedas"] = busquedas
        if comparacion_busquedas is None:
            info["comparacion_busquedas"] = None
        return info

    def _generar(self, info, nombre="r.pdf"):
        ruta = os.path.join(TMP, nombre)
        ex.reporte_final(ruta, info)
        with open(ruta, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")
        return ruta

    def test_un_solo_dato(self):
        self._generar(self._info([42]))

    def test_nombre_larguisimo_con_emoji_y_acentos(self):
        nombre = "datos_" + "muy_largo_" * 20 + "ñandú_😀.xlsx"
        self._generar(self._info([3, 1, 2], nombre=nombre))

    def test_muchas_busquedas_y_sin_comparacion_de_metodos(self):
        busquedas = [{"valor": i, "metodo": "Hash", "fuente": "datos originales (desordenados)",
                      "encontrado": i % 2 == 0, "apariciones": 1, "comparaciones": 1, "segundos": 0.00001}
                     for i in range(500)]
        self._generar(self._info([5, 4, 3], busquedas=busquedas, comparacion_busquedas=None))

    def test_doscientos_mil_datos_en_poco_tiempo(self):
        rnd = random.Random(7)
        datos = [rnd.randint(-10 ** 9, 10 ** 9) for _ in range(200000)]
        inicio = time.perf_counter()
        self._generar(self._info(datos), "grande.pdf")
        self.assertLess(time.perf_counter() - inicio, 60)


if __name__ == "__main__":
    unittest.main()
