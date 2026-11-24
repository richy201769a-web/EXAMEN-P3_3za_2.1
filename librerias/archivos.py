"""
LIBRERIA PROPIA - MANEJO DE ARCHIVOS TXT y XLSX

Lectura segura:
    * Solo extensiones .txt y .xlsx (lista blanca).
    * Se revisa el CONTENIDO real, no solo la extension (un .exe o un .xlsx
      renombrado a .txt se detecta y se rechaza).
    * Limites de tamano y de cantidad de registros (evita que un archivo
      gigante o una "bomba zip" congele el programa).
    * Cada dato se valida como entero; si hay datos invalidos se informa la
      linea o celda exacta y el archivo NO se carga a medias.

Escritura segura:
    * Se escribe primero un archivo temporal y luego se reemplaza (si algo
      falla a la mitad no queda un archivo corrupto).
    * En XLSX los textos se protegen contra "inyeccion de formulas"
      (=, +, -, @ al inicio).

Librerias usadas: os y openpyxl (permitidas por el examen).
"""

import os

from librerias.validacion import es_entero_texto, ErrorEntrada, MAX_DIGITOS

EXTENSIONES = (".txt", ".xlsx")
MAX_BYTES = 20 * 1024 * 1024        # 20 MB
MAX_REGISTROS = 500_000
MAX_ERRORES_MOSTRADOS = 8


class ErrorArchivo(Exception):
    """Error con mensaje listo para mostrar al usuario."""


# ----------------------------------------------------------------------
# Revisiones comunes
# ----------------------------------------------------------------------
def _extension(ruta):
    return os.path.splitext(ruta)[1].lower()


def _revisar_ruta(ruta):
    if not isinstance(ruta, str) or ruta.strip() == "":
        raise ErrorArchivo("No se indicó ningún archivo.")
    if "\x00" in ruta:
        raise ErrorArchivo("La ruta del archivo contiene caracteres no válidos.")
    if not os.path.exists(ruta):
        raise ErrorArchivo(f"El archivo no existe:\n{ruta}")
    if os.path.isdir(ruta):
        raise ErrorArchivo("Seleccionaste una carpeta, no un archivo.")
    if not os.path.isfile(ruta):
        raise ErrorArchivo("La ruta no es un archivo normal.")
    ext = _extension(ruta)
    if ext not in EXTENSIONES:
        raise ErrorArchivo(f"Formato '{ext or 'sin extensión'}' no permitido. "
                           "Solo se aceptan archivos .txt y .xlsx.")
    tam = os.path.getsize(ruta)
    if tam == 0:
        raise ErrorArchivo("El archivo está vacío (0 bytes).")
    if tam > MAX_BYTES:
        raise ErrorArchivo(f"El archivo pesa {tam / 1048576:.1f} MB; el máximo permitido es "
                           f"{MAX_BYTES // 1048576} MB.")
    return ext, tam


def _cabecera(ruta, n=8):
    with open(ruta, "rb") as f:
        return f.read(n)


def _resumen_errores(errores, total_errores):
    texto = "\n".join("  • " + e for e in errores)
    if total_errores > len(errores):
        texto += f"\n  … y {total_errores - len(errores)} error(es) más."
    return texto


# ----------------------------------------------------------------------
# Lectura TXT
# ----------------------------------------------------------------------
def _decodificar(contenido):
    if contenido.startswith(b"\xff\xfe") or contenido.startswith(b"\xfe\xff"):
        try:
            return contenido.decode("utf-16")
        except UnicodeDecodeError:
            raise ErrorArchivo("El archivo dice ser UTF-16 pero está dañado.")
    if b"\x00" in contenido:
        raise ErrorArchivo("El archivo no es de texto (contiene bytes binarios). "
                           "¿Es un programa o un archivo renombrado a .txt?")
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        # TXT guardado como "ANSI" en el Bloc de notas de Windows (p. ej. un encabezado con acentos).
        # Los digitos son iguales en ambas codificaciones, asi que leerlo como cp1252 es seguro.
        return contenido.decode("cp1252", errors="replace")


def _es_encabezado_txt(linea):
    """Primera linea solo con letras/espacios (p. ej. «Numero» o «Números»): es un titulo, no un dato."""
    hay_letra = False
    for c in linea:
        if c.isdigit():
            return False
        if c.isalpha():
            hay_letra = True
        elif c not in " _-.:":
            return False
    return hay_letra and len(linea) <= 40


def leer_txt(ruta):
    with open(ruta, "rb") as f:
        contenido = f.read(MAX_BYTES + 1)
    if contenido.startswith(b"PK\x03\x04"):
        raise ErrorArchivo("Este archivo .txt en realidad es un ZIP/XLSX renombrado. "
                           "Cámbiale la extensión a .xlsx o usa un TXT real.")
    if contenido.startswith(b"MZ"):
        raise ErrorArchivo("Este archivo .txt en realidad es un ejecutable. Se rechazó por seguridad.")
    texto = _decodificar(contenido)

    datos = []
    errores = []
    total_errores = 0
    num_linea = 0
    encabezado = None
    primera = True
    for linea in texto.splitlines():
        num_linea += 1
        limpia = linea.strip()
        if limpia == "" or limpia.startswith("#"):       # lineas vacias o comentarios
            continue
        if primera:
            primera = False
            if _es_encabezado_txt(limpia):               # encabezado opcional, como en Excel
                encabezado = limpia
                continue
        tokens = limpia.replace(";", " ").replace("\t", " ").split()
        malo = None
        for token in tokens:
            if not es_entero_texto(token):
                malo = token
                break
        if malo is not None:                              # la linea se reporta una sola vez
            total_errores += 1
            if len(errores) < MAX_ERRORES_MOSTRADOS:
                errores.append(f"Línea {num_linea}: '{_mostrar(limpia, 30)}' {_motivo(malo)}")
            continue
        for token in tokens:
            datos.append(int(token))
        if len(datos) > MAX_REGISTROS:
            raise ErrorArchivo(f"El archivo tiene más de {MAX_REGISTROS:,} números; "
                               "es demasiado grande para este sistema.")
    if total_errores > 0:
        raise ErrorArchivo(f"El archivo tiene {total_errores} línea(s) con datos no válidos y no se cargó:\n"
                           + _resumen_errores(errores, total_errores))
    return datos, encabezado, None


# ----------------------------------------------------------------------
# Lectura XLSX
# ----------------------------------------------------------------------
def _columna(n):
    letras = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        letras = chr(65 + r) + letras
    return letras


def _convertir_celda(valor):
    """Regresa (entero, None) o (None, motivo_del_error). (None, None) = celda vacia."""
    if valor is None:
        return None, None
    if isinstance(valor, bool):
        return None, "es un valor lógico (VERDADERO/FALSO)"
    if isinstance(valor, int):
        if valor > 10 ** MAX_DIGITOS - 1 or valor < -(10 ** MAX_DIGITOS - 1):
            return None, "es demasiado grande"
        return valor, None
    if isinstance(valor, float):
        if valor != valor or valor in (float("inf"), float("-inf")):
            return None, "no es un número válido"
        if not valor.is_integer():
            return None, "tiene decimales; solo se aceptan enteros"
        if abs(valor) > 10 ** MAX_DIGITOS - 1:
            return None, "es demasiado grande"
        return int(valor), None
    if isinstance(valor, str):
        limpio = valor.strip()
        if limpio == "":
            return None, None
        if es_entero_texto(limpio):
            return int(limpio), None
        return None, _motivo(limpio)
    return None, f"tiene un tipo no permitido ({type(valor).__name__}, p. ej. una fecha)"


def leer_xlsx(ruta):
    cab = _cabecera(ruta)
    if cab.startswith(b"\xd0\xcf\x11\xe0"):
        raise ErrorArchivo("El archivo está protegido con contraseña o es un Excel antiguo (.xls). "
                           "Guárdalo como .xlsx sin contraseña.")
    if not cab.startswith(b"PK\x03\x04"):
        raise ErrorArchivo("El archivo no es un XLSX real (su contenido no corresponde a Excel). "
                           "¿Es un TXT u otro archivo renombrado a .xlsx?")
    try:
        import openpyxl
    except ImportError:
        raise ErrorArchivo("Falta la librería openpyxl. Instálala con:  python -m pip install openpyxl")
    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception:
        raise ErrorArchivo("No se pudo abrir el XLSX: está dañado o no es un libro de Excel válido.")

    try:
        if len(libro.worksheets) == 0:
            raise ErrorArchivo("El libro de Excel no tiene hojas.")
        hoja = libro.worksheets[0]
        datos = []
        errores = []
        total_errores = 0
        encabezado = None
        primera_fila = True
        num_fila = 0
        for fila in hoja.iter_rows(min_row=1, values_only=True):
            num_fila += 1
            if num_fila > MAX_REGISTROS + 1:
                raise ErrorArchivo(f"La hoja tiene más de {MAX_REGISTROS:,} filas; es demasiado grande.")
            convertidos = []
            hay_algo = False
            for num_col in range(len(fila)):
                valor = fila[num_col]
                entero, motivo = _convertir_celda(valor)
                if entero is None and motivo is None:
                    continue
                hay_algo = True
                convertidos.append((num_col, valor, entero, motivo))
            if not hay_algo:
                continue
            if primera_fila:
                primera_fila = False
                # Encabezado: la primera fila con datos donde todo es texto no numerico
                es_encabezado = True
                for _, valor, entero, _m in convertidos:
                    if not isinstance(valor, str) or entero is not None:
                        es_encabezado = False
                if es_encabezado:
                    encabezado = ", ".join(str(c[1]).strip() for c in convertidos)
                    continue
            for num_col, valor, entero, motivo in convertidos:
                if motivo is None:
                    datos.append(entero)
                    if len(datos) > MAX_REGISTROS:
                        raise ErrorArchivo(f"La hoja tiene más de {MAX_REGISTROS:,} números.")
                else:
                    total_errores += 1
                    if len(errores) < MAX_ERRORES_MOSTRADOS:
                        errores.append(f"Celda {_columna(num_col + 1)}{num_fila}: "
                                       f"'{_mostrar(str(valor))}' {motivo}")
        if total_errores > 0:
            raise ErrorArchivo(f"La hoja '{hoja.title}' tiene {total_errores} dato(s) no válidos "
                               "y no se cargó:\n" + _resumen_errores(errores, total_errores))
        return datos, encabezado, hoja.title
    finally:
        libro.close()


# ----------------------------------------------------------------------
# Funcion principal de lectura
# ----------------------------------------------------------------------
def leer_archivo(ruta):
    """Lee un TXT o XLSX de enteros. Regresa un diccionario con los datos y
    la informacion del archivo, o lanza ErrorArchivo con la causa."""
    ext, tam = _revisar_ruta(ruta)
    try:
        if ext == ".txt":
            datos, encabezado, hoja = leer_txt(ruta)
            formato = "TXT"
        else:
            datos, encabezado, hoja = leer_xlsx(ruta)
            formato = "XLSX"
    except PermissionError:
        raise ErrorArchivo("No hay permiso para leer el archivo (¿está abierto en Excel o protegido?).")
    except ErrorEntrada as e:
        raise ErrorArchivo(str(e))
    except OSError as e:
        raise ErrorArchivo(f"No se pudo leer el archivo: {e.strerror or e}")
    if len(datos) == 0:
        raise ErrorArchivo("El archivo no contiene ningún número entero.")
    return {
        "datos": datos,
        "formato": formato,
        "ruta": os.path.abspath(ruta),
        "nombre": os.path.basename(ruta),
        "bytes": tam,
        "encabezado": encabezado,
        "hoja": hoja,
    }


# ----------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------
def proteger_texto_excel(texto):
    """Evita inyeccion de formulas: un texto que empieza con = + - @ se
    guarda como texto literal."""
    texto = str(texto)
    if texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + texto
    return texto


def _limpiar_meta(texto):
    """Una sola linea, sin caracteres de control."""
    return "".join(c if c.isprintable() else " " for c in str(texto))


def _reemplazar_seguro(ruta_temporal, ruta_final):
    try:
        os.replace(ruta_temporal, ruta_final)
    except PermissionError:
        try:
            os.remove(ruta_temporal)
        except OSError:
            pass
        raise ErrorArchivo("No se pudo guardar: el archivo de destino está abierto en otro "
                           "programa (¿Excel?) o no hay permiso de escritura.")


def guardar_txt(ruta, lista, metadatos=()):
    """Guarda un numero por linea. Los metadatos van al inicio como
    comentarios '# clave: valor' (este mismo sistema los ignora al leer)."""
    if _extension(ruta) != ".txt":
        raise ErrorArchivo("El archivo de salida debe tener extensión .txt")
    temporal = ruta + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8", newline="\n") as f:
            for clave, valor in metadatos:
                f.write(f"# {_limpiar_meta(clave)}: {_limpiar_meta(valor)}\n")
            for valor in lista:
                f.write(str(valor) + "\n")
    except OSError as e:
        raise ErrorArchivo(f"No se pudo escribir el archivo: {e.strerror or e}")
    _reemplazar_seguro(temporal, ruta)


def guardar_xlsx(ruta, lista, metadatos=()):
    """Hoja 'Datos ordenados' (columna Numero) + hoja 'Resumen'."""
    if _extension(ruta) != ".xlsx":
        raise ErrorArchivo("El archivo de salida debe tener extensión .xlsx")
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise ErrorArchivo("Falta la librería openpyxl. Instálala con:  python -m pip install openpyxl")
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Datos ordenados"
    hoja.append(["Numero"])
    hoja["A1"].font = Font(bold=True, color="FFFFFF")
    hoja["A1"].fill = PatternFill("solid", fgColor="1F4E79")
    for valor in lista:
        hoja.append([valor])
    hoja.column_dimensions["A"].width = 16

    resumen = libro.create_sheet("Resumen")
    resumen.append(["Concepto", "Valor"])
    for celda in resumen[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E79")
    for clave, valor in metadatos:
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            resumen.append([proteger_texto_excel(clave), valor])
        else:
            resumen.append([proteger_texto_excel(clave), proteger_texto_excel(_limpiar_meta(valor))])
    resumen.column_dimensions["A"].width = 30
    resumen.column_dimensions["B"].width = 60

    temporal = ruta + ".tmp"
    try:
        libro.save(temporal)
    except OSError as e:
        raise ErrorArchivo(f"No se pudo escribir el archivo: {e.strerror or e}")
    _reemplazar_seguro(temporal, ruta)


# ----------------------------------------------------------------------
# Mensajes
# ----------------------------------------------------------------------
def _mostrar(texto, largo=20):
    texto = "".join(c if c.isprintable() else "?" for c in texto)
    return texto if len(texto) <= largo else texto[:largo] + "…"


def _motivo(token):
    sin_signo = token[1:] if token[:1] in "+-" else token
    if sin_signo == "":
        return "es solo un signo"
    if all(c in "0123456789" for c in sin_signo) and len(sin_signo) > MAX_DIGITOS:
        return f"tiene más de {MAX_DIGITOS} dígitos"
    if any(c in ".," for c in sin_signo) and any(c in "0123456789" for c in sin_signo):
        return "tiene decimales o separador de miles; solo se aceptan enteros"
    if any(c.isdigit() and c not in "0123456789" for c in sin_signo):
        return "usa dígitos no estándar"
    if "e" in sin_signo.lower() and len(sin_signo) > 1 and all(c in "0123456789eE+-." for c in sin_signo):
        return "está en notación científica; escribe el entero completo"
    return "no es un número entero"

