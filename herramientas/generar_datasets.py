"""
Genera los archivos que usan las PRUEBAS AUTOMATICAS (el programa principal
no trae datos precargados: el usuario carga su propio archivo):

  pruebas/datos/dataset_20000_duplicados.txt -> 20,000 enteros, mismo formato que
                                                 los del profesor (1..100,000, un
                                                 numero por linea, ~25 % repetidos).
  pruebas/datos/pruebas_error/*              -> archivos con errores tipicos para
                                                 probar las validaciones.

Uso:  python herramientas/generar_datasets.py
(Es una herramienta aparte; el sistema principal no la necesita.)
"""

import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(BASE, "pruebas", "datos")
ERRORES = os.path.join(DATOS, "pruebas_error")


def generar_dataset(n, semilla=2026):
    """75 % de valores aleatorios en 1..100000 y 25 % copias de valores ya
    generados (duplicados), todo revuelto. Es la misma proporcion que tienen
    los datasets entregados (1000 -> 748 distintos)."""
    rnd = random.Random(semilla)
    unicos = int(n * 0.75)
    datos = [rnd.randint(1, 100_000) for _ in range(unicos)]
    while len(datos) < n:
        datos.append(datos[rnd.randrange(unicos)])
    rnd.shuffle(datos)
    return datos


def escribir(nombre, contenido, binario=False):
    ruta = os.path.join(ERRORES, nombre)
    modo = "wb" if binario else "w"
    with open(ruta, modo, **({} if binario else {"encoding": "utf-8", "newline": ""})) as f:
        f.write(contenido)


def generar_archivos_error():
    os.makedirs(ERRORES, exist_ok=True)
    escribir("01_vacio.txt", "")
    escribir("02_solo_espacios.txt", "   \n\n  \n")
    escribir("03_con_letras.txt", "10\n20\nabc\n40\n")
    escribir("04_decimales.txt", "10\n3.5\n7,25\n8\n")
    escribir("05_notacion_cientifica.txt", "1e5\n200\n")
    escribir("06_inyeccion_sql.txt", "10\n' OR 1=1 --\n20\n; DROP TABLE datos;\n")
    escribir("07_numero_gigante.txt", "5\n" + "9" * 40 + "\n")
    escribir("08_digitos_unicode.txt", "10\n１２３\n٣\n")
    escribir("09_binario_disfrazado.txt", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00", binario=True)
    escribir("10_xlsx_falso.xlsx", "esto no es un excel\n1\n2\n")
    escribir("11_formato_no_permitido.csv", "1,2,3\n")
    escribir("12_valido_con_espacios_y_lineas_vacias.txt", "  15 \r\n\r\n-3\r\n+7\r\n\t42\t\r\n")
    escribir("13_utf8_con_bom.txt", "﻿100\n50\n75\n")
    escribir("14_separado_por_espacios.txt", "5 4 3; 2 1\n")
    escribir("15_signo_suelto.txt", "10\n-\n20\n")
    escribir("16_inyeccion_formula.txt", "=CMD|' /C calc'!A0\n1\n")

    # XLSX con problemas (requiere openpyxl)
    try:
        import openpyxl
        import datetime
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "Datos"
        for fila in (["Numero"], [10], [2.5], ["hola"], [True], [datetime.date(2026, 1, 1)], [30.0], [None], [40]):
            hoja.append(fila)
        libro.save(os.path.join(ERRORES, "17_xlsx_con_errores.xlsx"))

        libro = openpyxl.Workbook()
        libro.active.append(["Numero"])
        libro.save(os.path.join(ERRORES, "18_xlsx_solo_encabezado.xlsx"))

        libro = openpyxl.Workbook()
        hoja = libro.active
        for fila in ([5, 3], [8, None], ["  12 ", 1.0]):
            hoja.append(fila)
        libro.save(os.path.join(ERRORES, "19_xlsx_valido_varias_columnas.xlsx"))
    except ImportError:
        print("openpyxl no instalado: se omiten los XLSX de prueba.")


if __name__ == "__main__":
    os.makedirs(DATOS, exist_ok=True)
    datos = generar_dataset(20_000)
    ruta = os.path.join(DATOS, "dataset_20000_duplicados.txt")
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        for v in datos:
            f.write(f"{v}\n")
    distintos = len(set(datos))
    print(f"Generado {ruta}: {len(datos):,} números, {distintos:,} distintos, "
          f"{len(datos) - distintos:,} repetidos.")
    generar_archivos_error()
    print(f"Archivos de prueba de errores en {ERRORES}")
