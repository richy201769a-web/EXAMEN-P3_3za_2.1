"""Funciones de apoyo para las pruebas (sin usar sorted() ni .sort())."""

import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(BASE, "pruebas", "datos")     # archivos SOLO para las pruebas automaticas
ERRORES = os.path.join(DATOS, "pruebas_error")
TMP = os.path.join(BASE, "pruebas", "_tmp")


def conteo(lista):
    """Cuantas veces aparece cada valor: sirve para comprobar que el
    ordenamiento no perdio ni invento datos."""
    c = {}
    for v in lista:
        c[v] = c.get(v, 0) + 1
    return c


def aleatorios(n, semilla, minimo=-1000, maximo=1000):
    rnd = random.Random(semilla)
    return [rnd.randint(minimo, maximo) for _ in range(n)]


def limpiar_tmp():
    """Deja la carpeta temporal de pruebas vacia (archivos y subcarpetas)."""
    import shutil
    import stat
    os.makedirs(TMP, exist_ok=True)
    for nombre in os.listdir(TMP):
        ruta = os.path.join(TMP, nombre)
        if os.path.isdir(ruta):
            shutil.rmtree(ruta, ignore_errors=True)
        else:
            os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)
            os.remove(ruta)


def escribir_tmp(nombre, contenido, binario=False):
    os.makedirs(TMP, exist_ok=True)
    ruta = os.path.join(TMP, nombre)
    if binario:
        with open(ruta, "wb") as f:
            f.write(contenido)
    else:
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
    return ruta
