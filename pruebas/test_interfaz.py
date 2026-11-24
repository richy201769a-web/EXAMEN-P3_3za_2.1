"""
Pruebas de la interfaz grafica: flujo completo del proceso, bloqueo del
reporte final hasta terminar los 4 pasos, cancelacion y validaciones.
(Se omiten automaticamente si la computadora no tiene pantalla.)
"""

import os
import unittest
import tkinter as tk
import tkinter.messagebox as mb
import tkinter.filedialog as fd

from pruebas.utilidades import DATOS, ERRORES, TMP, limpiar_tmp


def _hay_pantalla():
    try:
        r = tk.Tk()
        r.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_hay_pantalla(), "No hay pantalla para probar la interfaz")
class FlujoDeLaInterfaz(unittest.TestCase):

    def setUp(self):
        limpiar_tmp()
        self.mensajes = []
        self.originales = {n: getattr(mb, n) for n in ("showwarning", "showinfo", "showerror", "askyesno")}
        self.dialogo = fd.asksaveasfilename
        for n in ("showwarning", "showinfo", "showerror"):
            setattr(mb, n, lambda *a, **k: self.mensajes.append(a[0]))
        mb.askyesno = lambda *a, **k: False
        import interfaz
        self.app = interfaz.Aplicacion()
        self.app.withdraw()

    def tearDown(self):
        self.app.update()                      # termina dibujos pendientes de las graficas
        self.app.destroy()
        for n, f in self.originales.items():
            setattr(mb, n, f)
        fd.asksaveasfilename = self.dialogo

    def test_proceso_completo_y_reporte_final(self):
        app = self.app
        self.assertFalse(app.btn_pdf.habilitado)
        app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        self.assertTrue(app.hecho["cargar"])
        self.assertFalse(app.btn_pdf.habilitado)

        app.var_algoritmo.set("HeapSort")
        app._accion_ordenar()
        self.assertTrue(app.resultado["verificado"])
        self.assertTrue(app.btn_guardar_datos.habilitado)
        self.assertFalse(app.btn_pdf.habilitado)

        app.var_metodo.set("Binaria")
        app.var_buscar.set(str(app.resultado["lista"][10]))
        app._accion_buscar()
        self.assertTrue(app.busquedas[-1]["encontrado"])
        self.assertFalse(app.btn_pdf.habilitado)            # falta comparar

        app._solo_rapidos()
        app._accion_comparar()
        self.assertTrue(app.hecho["comparar"])
        self.assertTrue(app.btn_pdf.habilitado)              # ahora si

        ruta = os.path.join(TMP, "reporte_gui.pdf")
        fd.asksaveasfilename = lambda **k: ruta
        app._exportar_reporte_final()
        with open(ruta, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")

        app._cargar(os.path.join(DATOS, "dataset_5000_duplicados.xlsx"))
        self.assertFalse(app.hecho["ordenar"] or app.hecho["buscar"] or app.hecho["comparar"])
        self.assertFalse(app.btn_pdf.habilitado)

    def test_reporte_bloqueado_aunque_se_llame_directo(self):
        self.app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        self.app._exportar_reporte_final()
        self.assertEqual(self.mensajes[-1], "Proceso incompleto")

    def test_cancelar_ordenamiento(self):
        app = self.app
        app._cargar(os.path.join(DATOS, "dataset_20000_duplicados.txt"))
        app.var_algoritmo.set("Burbuja")
        app.after(800, app._pedir_cancelar)
        app._accion_ordenar()
        self.assertIsNone(app.resultado)
        self.assertFalse(app.hecho["ordenar"])
        self.assertFalse(app.ocupado)

    def test_intercalacion_con_archivos_ordenados_antes(self):
        app = self.app
        app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        rutas = {}
        for clave, orden, ext in (("A", "asc", ".txt"), ("B", "asc", ".xlsx"), ("C", "desc", ".txt")):
            app.var_orden.set(orden)
            app._accion_ordenar()
            app.var_formato.set(ext)
            rutas[clave] = os.path.join(TMP, f"ordenado_{clave}{ext}")
            fd.asksaveasfilename = lambda **k: rutas[clave]
            app._exportar_datos()
        salida = os.path.join(TMP, "intercalado.txt")
        fd.asksaveasfilename = lambda **k: salida
        app.rutas_inter = {"A": rutas["A"], "B": rutas["B"]}
        app._accion_intercalar()
        self.assertTrue(app.intercalacion["verificado"])
        self.assertEqual(app.intercalacion["n"], 2000)
        app.intercalacion = None
        app.rutas_inter = {"A": rutas["A"], "B": rutas["C"]}          # ascendente + descendente
        app._accion_intercalar()
        self.assertIsNone(app.intercalacion)
        self.assertEqual(self.mensajes[-1], "Órdenes distintos")
        app.rutas_inter = {"A": os.path.join(DATOS, "dataset_1000_duplicados.txt"), "B": rutas["B"]}
        app._accion_intercalar()
        self.assertEqual(self.mensajes[-1], "Archivo sin ordenar")

    def test_acciones_repetidas_mientras_hay_un_proceso(self):
        """Si ya hay un proceso corriendo, ningun boton debe lanzar otro (doble clic, Enter, etc.)."""
        app = self.app
        app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        antes = (app.resultado, list(app.busquedas), list(app.comparacion), app.laboratorio)
        app.ocupado = True
        try:
            app._accion_ordenar()
            app.var_buscar.set("5")
            app._accion_buscar()
            app._accion_comparar_busquedas()
            app._accion_comparar()
            app._accion_laboratorio()
            app._exportar_datos()
            app._exportar_reporte_final()
            app._accion_intercalar()
            app._cargar(os.path.join(DATOS, "dataset_5000_duplicados.xlsx"))
        finally:
            app.ocupado = False
        self.assertEqual((app.resultado, app.busquedas, app.comparacion, app.laboratorio), antes)
        self.assertEqual(len(app.originales), 1000)

    def test_busqueda_vacia_o_solo_signo(self):
        app = self.app
        app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        app.var_fuente.set("originales")
        app.var_metodo.set("Secuencial")
        for texto in ("", "-", "+"):
            app.var_buscar.set(texto)
            app._accion_buscar()
            self.assertEqual(self.mensajes[-1], "Valor no válido")
        self.assertEqual(app.busquedas, [])

    def test_txt_con_encabezado_se_muestra(self):
        ruta = os.path.join(TMP, "con_titulo.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("Numero\n30\n10\n20\n")
        self.app._cargar(ruta)
        self.assertEqual(self.app.originales, [30, 10, 20])
        self.assertIn("Numero", self.app.stats["detalle_hoja"])

    def test_flujo_con_negativos_y_un_valor_extremo(self):
        """Archivo con negativos y un valor enorme: todo el proceso funciona y el PDF se genera."""
        datos = [((i * 7919) % 100001) - 50000 for i in range(3000)]
        datos[1500] = 470000000
        ruta = os.path.join(TMP, "extremos.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(str(v) for v in datos) + "\n")
        app = self.app
        app._cargar(ruta)
        self.assertEqual(len(app.originales), 3000)
        for orden in ("asc", "desc"):
            app.var_orden.set(orden)
            app.var_algoritmo.set("QuickSort")
            app._accion_ordenar()
            self.assertTrue(app.resultado["verificado"])
        app.var_buscar.set("470000000")
        app._accion_buscar()
        self.assertTrue(app.busquedas[-1]["encontrado"])
        app._solo_rapidos()
        app._accion_comparar()
        salida = os.path.join(TMP, "reporte_extremos_gui.pdf")
        fd.asksaveasfilename = lambda **k: salida
        app._exportar_reporte_final()
        with open(salida, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")

    def test_graficas_llegan_al_total_y_al_maximo(self):
        """Con el archivo de 20,000 la grafica llega a la posicion 20,000 y al valor maximo real."""
        app = self.app
        app._cargar(os.path.join(DATOS, "dataset_20000_duplicados.txt"))
        datos = app.originales
        mayor = datos[0]
        for v in datos:
            if v > mayor:
                mayor = v
        for grafica in (app.graf_carga,):
            ax = grafica.figura.axes[0]
            self.assertEqual(ax.get_xticks()[-1], 20000)
            self.assertEqual(ax.get_yticklabels()[-1].get_text(), f"{mayor:,}")
        app.var_algoritmo.set("RadixSort")
        app._accion_ordenar()
        for ax in app.graf_orden.figura.axes:
            self.assertEqual(ax.get_xticks()[-1], 20000)
            self.assertEqual(ax.get_yticklabels()[-1].get_text(), f"{mayor:,}")

    def test_validaciones(self):
        app = self.app
        app._accion_ordenar()
        self.assertEqual(self.mensajes[-1], "Sin datos")
        app._cargar(os.path.join(ERRORES, "06_inyeccion_sql.txt"))
        self.assertEqual(self.mensajes[-1], "Archivo no válido")
        app._cargar(os.path.join(DATOS, "dataset_1000_duplicados.txt"))
        app.var_fuente.set("originales")
        app.var_metodo.set("Binaria")
        app.var_buscar.set("10")
        app._accion_buscar()
        self.assertEqual(self.mensajes[-1], "Búsqueda binaria no aplicable")
        app.ent_buscar.delete(0, "end")
        app.ent_buscar.insert(0, "' OR 1=1 --")
        self.assertEqual(app.var_buscar.get(), "")
        app.var_algoritmo.set("QuickSort")
        app._accion_ordenar()
        fd.asksaveasfilename = lambda **k: app.info["ruta"]
        app._exportar_datos()
        self.assertEqual(self.mensajes[-1], "Operación no permitida")


if __name__ == "__main__":
    unittest.main()
