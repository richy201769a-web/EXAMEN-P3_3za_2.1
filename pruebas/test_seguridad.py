"""
Pruebas de seguridad y de cumplimiento de restricciones.

El sistema no usa base de datos, asi que la inyeccion SQL no puede ejecutarse;
aun asi se comprueba que cualquier texto de ataque (SQL, comandos, rutas,
scripts, formulas de Excel, bytes nulos, entradas gigantes) se RECHAZA antes
de llegar a la logica, y que el codigo no contiene funciones peligrosas
(eval, exec, os.system, subprocess, pickle) ni ordenamientos prohibidos.
"""

import ast
import os
import unittest

import openpyxl

from librerias import validacion as val
from librerias import archivos as ar
from pruebas.utilidades import BASE, TMP, limpiar_tmp, escribir_tmp

ATAQUES = [
    "' OR '1'='1", "1 OR 1=1", "1; DROP TABLE datos;--", "1' --", "\" OR \"\"=\"", "1 UNION SELECT * FROM users",
    "admin'--", "1); DELETE FROM datos; --", "%27%20OR%201=1",
    "; rm -rf /", "&& del C:\\Windows", "| shutdown /s", "$(whoami)", "`id`",
    "../../etc/passwd", "..\\..\\Windows\\System32", "C:\\Windows\\system.ini",
    "<script>alert(1)</script>", "javascript:alert(1)",
    "=CMD|' /C calc'!A0", "@SUM(1+1)", "+1+1", "-1-1",
    "__import__('os').system('dir')", "eval('2+2')", "exec('x')", "1+1", "2*3", "10/2", "1e3", "0x1F", "0b101",
    "1_000", "1,000", "1.000", "١٢٣", "１２３", "Ⅻ", "½", "∞", "NaN", "inf", "-inf", "None", "True",
    "1\x00", "\x00", "1\n2", "1\t2", "+-5", "--5", "++5", "5-", "- 5", "",
    "9" * 16, "9" * 100, "9" * 100000,
]


class ValidacionEntradas(unittest.TestCase):

    def test_ataques_rechazados_por_convertir_entero(self):
        for ataque in ATAQUES:
            with self.subTest(entrada=ataque[:40]):
                with self.assertRaises(val.ErrorEntrada):
                    val.convertir_entero(ataque)

    def test_ataques_bloqueados_en_vivo(self):
        """El campo de busqueda ni siquiera deja escribirlos (validatecommand)."""
        for ataque in ATAQUES:
            if ataque in ("",):
                continue
            with self.subTest(entrada=ataque[:40]):
                self.assertFalse(val.caracter_permitido_busqueda(ataque))

    def test_entradas_validas(self):
        casos = {"0": 0, "5": 5, "-5": -5, "+5": 5, "  42  ": 42, "007": 7, "-0": 0,
                 "999999999999999": 999999999999999, "-999999999999999": -999999999999999}
        for texto, esperado in casos.items():
            with self.subTest(entrada=texto):
                self.assertEqual(val.convertir_entero(texto), esperado)

    def test_escritura_parcial_permitida_en_vivo(self):
        for texto in ("", "-", "+", "1", "-12", "+999"):
            self.assertTrue(val.caracter_permitido_busqueda(texto))

    def test_no_texto(self):
        for valor in (None, 5, 3.2, b"5", ["5"]):
            with self.assertRaises(val.ErrorEntrada):
                val.convertir_entero(valor)

    def test_mensajes_no_reflejan_entrada_gigante(self):
        try:
            val.convertir_entero("x" * 5000)
        except val.ErrorEntrada as e:
            self.assertLess(len(str(e)), 200)


class ArchivosMaliciosos(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()

    def test_ejecutable_renombrado(self):
        ruta = escribir_tmp("virus.txt", b"MZ\x90\x00" + b"\x00" * 100, binario=True)
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(ruta)

    def test_zip_renombrado_a_txt(self):
        ruta = escribir_tmp("zip.txt", b"PK\x03\x04" + b"\x00" * 50, binario=True)
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(ruta)

    def test_xlsx_corrupto(self):
        ruta = escribir_tmp("roto.xlsx", b"PK\x03\x04basura-que-no-es-un-zip-valido", binario=True)
        with self.assertRaises(ar.ErrorArchivo):
            ar.leer_archivo(ruta)

    def test_xlsx_protegido_o_xls_antiguo(self):
        ruta = escribir_tmp("protegido.xlsx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100, binario=True)
        with self.assertRaises(ar.ErrorArchivo) as ctx:
            ar.leer_archivo(ruta)
        self.assertIn("contraseña", str(ctx.exception))

    def test_limite_de_tamano(self):
        original = ar.MAX_BYTES
        try:
            ar.MAX_BYTES = 100
            ruta = escribir_tmp("grande.txt", "1\n" * 200)
            with self.assertRaises(ar.ErrorArchivo):
                ar.leer_archivo(ruta)
        finally:
            ar.MAX_BYTES = original

    def test_limite_de_registros_txt_y_xlsx(self):
        original = ar.MAX_REGISTROS
        try:
            ar.MAX_REGISTROS = 50
            ruta = escribir_tmp("muchos.txt", "1\n" * 51)
            with self.assertRaises(ar.ErrorArchivo):
                ar.leer_archivo(ruta)
            ruta = os.path.join(TMP, "muchos.xlsx")
            libro = openpyxl.Workbook()
            for i in range(60):
                libro.active.append([i])
            libro.save(ruta)
            with self.assertRaises(ar.ErrorArchivo):
                ar.leer_archivo(ruta)
        finally:
            ar.MAX_REGISTROS = original

    def test_inyeccion_de_formulas_al_exportar_xlsx(self):
        ruta = os.path.join(TMP, "formula.xlsx")
        ar.guardar_xlsx(ruta, [1, 2], [("Archivo de origen", "=HYPERLINK(\"http://malo\",\"x\")"),
                                      ("Otro", "@SUM(A1)"), ("Normal", "datos.txt")])
        hoja = openpyxl.load_workbook(ruta)["Resumen"]
        self.assertTrue(hoja["B2"].value.startswith("'="))
        self.assertTrue(hoja["B3"].value.startswith("'@"))
        self.assertEqual(hoja["B4"].value, "datos.txt")

    def test_xlsx_con_formula_no_se_ejecuta(self):
        ruta = os.path.join(TMP, "con_formula.xlsx")
        libro = openpyxl.Workbook()
        libro.active.append([5])
        libro.active.append(["=1+1"])          # formula sin valor calculado
        libro.save(ruta)
        # data_only=True: no se evalua la formula; se trata como celda vacia
        self.assertEqual(ar.leer_archivo(ruta)["datos"], [5])


class RestriccionesDelExamen(unittest.TestCase):
    """Analiza el codigo fuente (arbol sintactico) de TODO el proyecto."""

    PROHIBIDOS_LLAMADA = {"sorted", "eval", "exec", "compile", "__import__"}
    PROHIBIDOS_METODO = {"sort", "sort_values", "sort_index", "nsmallest", "nlargest", "argsort", "system",
                         "popen"}
    PROHIBIDOS_MODULO = {"heapq", "bisect", "subprocess", "pickle", "marshal", "numpy", "sortedcontainers"}

    def archivos_python(self):
        for raiz, carpetas, archivos in os.walk(BASE):
            carpetas[:] = [c for c in carpetas if c not in ("__pycache__", ".git", "_tmp", "venv", ".venv")]
            for nombre in archivos:
                if nombre.endswith(".py"):
                    yield os.path.join(raiz, nombre)

    def test_no_se_usa_sort_sorted_ni_librerias_de_ordenamiento(self):
        hallazgos = []
        for ruta in self.archivos_python():
            with open(ruta, encoding="utf-8") as f:
                arbol = ast.parse(f.read(), filename=ruta)
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Call):
                    fn = nodo.func
                    if isinstance(fn, ast.Name) and fn.id in self.PROHIBIDOS_LLAMADA:
                        hallazgos.append(f"{os.path.relpath(ruta, BASE)}:{nodo.lineno} {fn.id}()")
                    if isinstance(fn, ast.Attribute) and fn.attr in self.PROHIBIDOS_METODO:
                        hallazgos.append(f"{os.path.relpath(ruta, BASE)}:{nodo.lineno} .{fn.attr}()")
                if isinstance(nodo, ast.Import):
                    for a in nodo.names:
                        if a.name.split(".")[0] in self.PROHIBIDOS_MODULO:
                            hallazgos.append(f"{os.path.relpath(ruta, BASE)}:{nodo.lineno} import {a.name}")
                if isinstance(nodo, ast.ImportFrom) and nodo.module and \
                        nodo.module.split(".")[0] in self.PROHIBIDOS_MODULO:
                    hallazgos.append(f"{os.path.relpath(ruta, BASE)}:{nodo.lineno} from {nodo.module}")
        self.assertEqual(hallazgos, [], "Se encontraron usos prohibidos:\n" + "\n".join(hallazgos))

    def test_la_interfaz_reutiliza_las_librerias_propias(self):
        with open(os.path.join(BASE, "interfaz.py"), encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        importados = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module == "librerias":
                for a in nodo.names:
                    importados.add(a.name)
        for modulo in ("ordenamiento_interno", "ordenamiento_externo", "busquedas", "archivos"):
            self.assertIn(modulo, importados)


if __name__ == "__main__":
    unittest.main()
