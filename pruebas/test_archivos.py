"""Pruebas de lectura y escritura de archivos TXT / XLSX."""

import os
import unittest

import openpyxl

from librerias import archivos as ar
from librerias import exportacion as ex
from librerias import ordenamiento_interno as oi
from pruebas.utilidades import DATOS, ERRORES, TMP, limpiar_tmp, escribir_tmp


class Lectura(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def test_dataset_txt_1000(self):
        info = ar.leer_archivo(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        self.assertEqual(info["formato"], "TXT")
        self.assertEqual(len(info["datos"]), 1000)
        self.assertEqual(info["datos"][:3], [44633, 16577, 106])

    def test_dataset_xlsx_5000_omite_encabezado(self):
        info = ar.leer_archivo(os.path.join(DATOS, "dataset_5000_duplicados.xlsx"))
        self.assertEqual(info["formato"], "XLSX")
        self.assertEqual(len(info["datos"]), 5000)
        self.assertEqual(info["encabezado"], "Numero")
        self.assertEqual(info["datos"][:2], [17198, 39022])

    def test_dataset_20000(self):
        self.assertEqual(len(ar.leer_archivo(os.path.join(DATOS, "dataset_20000_duplicados.txt"))["datos"]), 20000)

    def test_extension_en_mayusculas(self):
        ruta = escribir_tmp("DATOS.TXT", "3\n1\n")
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [3, 1])

    def test_formatos_tolerados(self):
        casos = {
            "crlf.txt": ("1\r\n2\r\n3\r\n", [1, 2, 3]),
            "sin_salto_final.txt": ("1\n2", [1, 2]),
            "espacios.txt": ("  4  \n\t5\t\n", [4, 5]),
            "lineas_vacias.txt": ("\n\n6\n\n\n7\n\n", [6, 7]),
            "signos.txt": ("+8\n-9\n-0\n", [8, -9, 0]),
            "ceros_izquierda.txt": ("007\n0010\n", [7, 10]),
            "comentarios.txt": ("# exportado\n# Algoritmo: X\n1\n2\n", [1, 2]),
            "punto_y_coma.txt": ("1;2;3\n", [1, 2, 3]),
            "solo_cr.txt": ("1\r2\r3", [1, 2, 3]),
        }
        for nombre, (contenido, esperado) in casos.items():
            with self.subTest(archivo=nombre):
                self.assertEqual(ar.leer_archivo(escribir_tmp(nombre, contenido))["datos"], esperado)

    def test_utf16_y_bom(self):
        ruta = escribir_tmp("utf16.txt", "10\n20\n".encode("utf-16"), binario=True)
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [10, 20])
        ruta = escribir_tmp("bom.txt", "﻿5\n6\n")
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [5, 6])

    def test_archivos_invalidos_se_rechazan(self):
        invalidos = ["01_vacio.txt", "02_solo_espacios.txt", "03_con_letras.txt", "04_decimales.txt",
                     "05_notacion_cientifica.txt", "06_inyeccion_sql.txt", "07_numero_gigante.txt",
                     "08_digitos_unicode.txt", "09_binario_disfrazado.txt", "10_xlsx_falso.xlsx",
                     "11_formato_no_permitido.csv", "15_signo_suelto.txt", "16_inyeccion_formula.txt",
                     "17_xlsx_con_errores.xlsx", "18_xlsx_solo_encabezado.xlsx"]
        for nombre in invalidos:
            with self.subTest(archivo=nombre):
                with self.assertRaises(ar.ErrorArchivo):
                    ar.leer_archivo(os.path.join(ERRORES, nombre))

    def test_archivos_validos_de_prueba(self):
        esperados = {
            "12_valido_con_espacios_y_lineas_vacias.txt": [15, -3, 7, 42],
            "13_utf8_con_bom.txt": [100, 50, 75],
            "14_separado_por_espacios.txt": [5, 4, 3, 2, 1],
            "19_xlsx_valido_varias_columnas.xlsx": [5, 3, 8, 12, 1],
        }
        for nombre, esperado in esperados.items():
            with self.subTest(archivo=nombre):
                self.assertEqual(ar.leer_archivo(os.path.join(ERRORES, nombre))["datos"], esperado)

    def test_mensaje_indica_linea_exacta(self):
        with self.assertRaises(ar.ErrorArchivo) as ctx:
            ar.leer_archivo(os.path.join(ERRORES, "03_con_letras.txt"))
        self.assertIn("Línea 3", str(ctx.exception))
        with self.assertRaises(ar.ErrorArchivo) as ctx:
            ar.leer_archivo(os.path.join(ERRORES, "17_xlsx_con_errores.xlsx"))
        self.assertIn("Celda A3", str(ctx.exception))

    def test_no_carga_a_medias(self):
        ruta = escribir_tmp("medio.txt", "1\n2\nx\n4\n")
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(ruta)

    def test_rutas_invalidas(self):
        for ruta in ("", "   ", os.path.join(TMP, "no_existe.txt"), TMP, "archivo\x00.txt", None):
            with self.subTest(ruta=ruta):
                with self.assertRaises(ar.ErrorArchivo):
                    ar.leer_archivo(ruta)

    def test_extensiones_no_permitidas(self):
        for nombre in ("datos.csv", "datos.exe", "datos.py", "datos.xls", "datos.json", "datos", "datos.txt.exe"):
            with self.subTest(archivo=nombre):
                ruta = escribir_tmp(nombre, "1\n2\n")
                with self.assertRaises(ar.ErrorArchivo):
                    ar.leer_archivo(ruta)

    def test_xlsx_numeros_como_texto_y_flotantes_enteros(self):
        ruta = os.path.join(TMP, "mixto.xlsx")
        libro = openpyxl.Workbook()
        for fila in (["Valores"], ["15"], [3.0], [-2], [" 8 "]):
            libro.active.append(fila)
        libro.save(ruta)
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [15, 3, -2, 8])

    def test_xlsx_sin_encabezado(self):
        ruta = os.path.join(TMP, "sin_encabezado.xlsx")
        libro = openpyxl.Workbook()
        for v in (9, 8, 7):
            libro.active.append([v])
        libro.save(ruta)
        info = ar.leer_archivo(ruta)
        self.assertEqual(info["datos"], [9, 8, 7])
        self.assertIsNone(info["encabezado"])

    def test_xlsx_con_huecos_y_filas_vacias(self):
        ruta = os.path.join(TMP, "huecos.xlsx")
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja["A1"] = "Numero"
        hoja["A3"] = 5
        hoja["A10"] = 6
        libro.save(ruta)
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [5, 6])


class Escritura(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def test_txt_ida_y_vuelta_con_metadatos(self):
        ruta = os.path.join(TMP, "salida.txt")
        datos = [1, 2, 2, 50, 99999]
        ar.guardar_txt(ruta, datos, [("Algoritmo", "QuickSort"), ("Tiempo", "0.5 ms")])
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        self.assertIn("# Algoritmo: QuickSort", contenido)
        self.assertIn("# Tiempo: 0.5 ms", contenido)
        self.assertEqual(ar.leer_archivo(ruta)["datos"], datos)     # los comentarios se ignoran

    def test_xlsx_ida_y_vuelta_con_resumen(self):
        ruta = os.path.join(TMP, "salida.xlsx")
        datos = [-3, 0, 8, 8, 1000]
        ar.guardar_xlsx(ruta, datos, [("Algoritmo utilizado", "HeapSort"), ("Tiempo (s)", 0.0123)])
        self.assertEqual(ar.leer_archivo(ruta)["datos"], datos)
        libro = openpyxl.load_workbook(ruta)
        self.assertEqual(libro.sheetnames, ["Datos ordenados", "Resumen"])
        self.assertEqual(libro["Resumen"]["B2"].value, "HeapSort")
        self.assertEqual(libro["Resumen"]["B3"].value, 0.0123)

    def test_extension_de_salida_incorrecta(self):
        with self.assertRaises(ar.ErrorArchivo):
            ar.guardar_txt(os.path.join(TMP, "x.xlsx"), [1])
        with self.assertRaises(ar.ErrorArchivo):
            ar.guardar_xlsx(os.path.join(TMP, "x.txt"), [1])

    def test_no_quedan_temporales(self):
        ar.guardar_txt(os.path.join(TMP, "a.txt"), [1, 2])
        ar.guardar_xlsx(os.path.join(TMP, "a.xlsx"), [1, 2])
        self.assertEqual(sorted_por_nombre(os.listdir(TMP)), ["a.txt", "a.xlsx"])

    def test_metadatos_con_saltos_de_linea_no_rompen_el_txt(self):
        ruta = os.path.join(TMP, "meta.txt")
        ar.guardar_txt(ruta, [1], [("Archivo", "malo\n999\n# x")])
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [1])

    def test_reporte_final_pdf(self):
        ruta = os.path.join(TMP, "reporte_final.pdf")
        ex.reporte_final(ruta, info_reporte_de_prueba())
        with open(ruta, "rb") as f:
            contenido = f.read()
        self.assertEqual(contenido[:4], b"%PDF")
        self.assertEqual(contenido.count(b"/Type /Page") - contenido.count(b"/Type /Pages"), 7)
        self.assertFalse(os.path.exists(ruta + ".tmp"))

    def test_reporte_final_con_intercalacion(self):
        info = info_reporte_de_prueba()
        info["intercalacion"] = {"a": "A.txt", "b": "B.txt", "salida": "C.txt", "orden": "Ascendente", "n": 4,
                                 "comparaciones": 3, "segundos": 0.001, "verificado": True, "datos": [1, 2, 3, 4]}
        ruta = os.path.join(TMP, "reporte_final_2.pdf")
        ex.reporte_final(ruta, info)
        self.assertTrue(os.path.getsize(ruta) > 1000)

    def test_pdf_requiere_extension(self):
        with self.assertRaises(ar.ErrorArchivo):
            ex.reporte_final(os.path.join(TMP, "x.txt"), info_reporte_de_prueba())


def info_reporte_de_prueba():
    datos = [5, 3, 9, 1, 7, 3] * 10
    ordenada, est = oi.quick_sort(datos)
    resultado = {"algoritmo": "QuickSort", "tipo": "Interno", "orden": "Ascendente", "segundos": 0.001,
                 "comparaciones": est["comparaciones"], "movimientos": est["movimientos"], "pasadas": 0,
                 "verificado": True, "lista": ordenada, "n": len(datos), "descendente": False}
    otro = dict(resultado, algoritmo="Mezcla Directa", tipo="Externo", segundos=0.004)
    return {
        "archivo": {"nombre": "prueba.txt", "formato": "TXT", "bytes": 120, "detalle_hoja": "Sin encabezado",
                    "n": len(datos), "minimo": 1, "maximo": 9, "distintos": 5, "repetidos": 55,
                    "estado_inicial": "Desordenado", "segundos_lectura": 0.0005},
        "original": datos, "resultado": resultado,
        "busquedas": [{"valor": 3, "metodo": "Binaria", "fuente": "datos ordenados", "encontrado": True,
                       "apariciones": 20, "comparaciones": 25, "segundos": 0.00001}],
        "comparacion_busquedas": {"valor": 3, "filas": [("Secuencial", 60, 0.0001, 20), ("Binaria", 25, 0.00001, 20),
                                                         ("Hash", 1, 0.000005, 20)]},
        "comparacion": [resultado, otro], "comparacion_orden": "Ascendente",
        "recomendaciones": [("Datos pequeños", "Inserción", "motivo de prueba")],
        "conclusiones": ["Conclusión de prueba."], "intercalacion": None,
        "pasos": [("Cargar datos", True, "prueba.txt", True), ("Intercalación", False, "Opcional", False)],
    }


def sorted_por_nombre(nombres):
    """Ordena nombres con la libreria propia (no se usa sorted())."""
    return oi.insercion(nombres)[0]


if __name__ == "__main__":
    unittest.main()
