"""
LIBRERIA PROPIA - VALIDACION DE ENTRADAS

Todo lo que escribe el usuario o viene de un archivo se valida con una
"lista blanca": solo se acepta lo que tiene forma de numero entero.
Cualquier otra cosa (texto, decimales, notacion cientifica, inyecciones
SQL, comandos, caracteres de control, digitos Unicode raros...) se rechaza
con un mensaje claro. Nunca se usa eval()/exec() con datos del usuario.
"""

DIGITOS = "0123456789"          # solo digitos ASCII (no acepta "１２" ni "٣")
MAX_DIGITOS = 15                # |n| < 10^15
LIMITE_VALOR = 10 ** MAX_DIGITOS - 1
MAX_LARGO_ENTRADA = MAX_DIGITOS + 1   # signo + digitos


class ErrorEntrada(Exception):
    """Error con mensaje listo para mostrar al usuario."""


def es_entero_texto(texto):
    """True si 'texto' es exactamente un entero: [+|-]digitos (ASCII)."""
    if not isinstance(texto, str) or len(texto) == 0:
        return False
    inicio = 1 if texto[0] in "+-" else 0
    if inicio == len(texto):
        return False
    if len(texto) - inicio > MAX_DIGITOS:
        return False
    for c in texto[inicio:]:
        if c not in DIGITOS:
            return False
    return True


def convertir_entero(texto, descripcion="El valor"):
    """Convierte un texto a int o lanza ErrorEntrada con la causa exacta."""
    if not isinstance(texto, str):
        raise ErrorEntrada(f"{descripcion} debe ser texto.")
    limpio = texto.strip()
    if limpio == "":
        raise ErrorEntrada(f"{descripcion} está vacío. Escribe un número entero.")
    sin_signo = limpio[1:] if limpio[0] in "+-" else limpio
    if sin_signo == "":
        raise ErrorEntrada(f"{descripcion} solo tiene un signo; falta el número.")
    for c in sin_signo:
        if c not in DIGITOS:
            if c in ".,":
                raise ErrorEntrada(f"{descripcion} '{_recortar(limpio)}' tiene decimales o separadores; "
                                   "solo se aceptan números enteros.")
            if c in "eE" and len(sin_signo) > 1:
                raise ErrorEntrada(f"{descripcion} '{_recortar(limpio)}' está en notación científica; "
                                   "escribe el entero completo.")
            if c.isdigit():
                raise ErrorEntrada(f"{descripcion} contiene dígitos no estándar ('{c}'); usa 0-9.")
            if not c.isprintable():
                raise ErrorEntrada(f"{descripcion} contiene caracteres de control no permitidos.")
            raise ErrorEntrada(f"{descripcion} '{_recortar(limpio)}' no es un número entero "
                               f"(carácter no permitido: '{c}').")
    if len(sin_signo) > MAX_DIGITOS:
        raise ErrorEntrada(f"{descripcion} es demasiado grande (máximo {MAX_DIGITOS} dígitos).")
    return int(limpio)


def validar_rango(valor, descripcion="El valor"):
    if valor > LIMITE_VALOR or valor < -LIMITE_VALOR:
        raise ErrorEntrada(f"{descripcion} {valor} está fuera del rango permitido "
                           f"(±{LIMITE_VALOR:,}).")
    return valor


def caracter_permitido_busqueda(texto_propuesto):
    """Validacion EN VIVO del campo de busqueda (tkinter validatecommand).
    Permite escribir solo un signo opcional al inicio y digitos ASCII."""
    if len(texto_propuesto) > MAX_LARGO_ENTRADA:
        return False
    if texto_propuesto in ("", "-", "+"):
        return True
    return es_entero_texto(texto_propuesto)


def _recortar(texto, largo=25):
    """Evita mostrar textos gigantes en los mensajes de error."""
    texto = "".join(c if c.isprintable() else "?" for c in texto)
    if len(texto) > largo:
        return texto[:largo] + "…"
    return texto
