"""Reglas comunes a las decisiones del revisor que le devuelven la idea al
autor con una explicación.

Son TRES puntos: rechazo en revisión de área (revision/router.py:rechazar),
rechazo en comité (comites/router.py:rechazar) y pedido de cambios
(revision/router.py:pedir_cambios). Los tres exigen lo mismo del texto, y la
regla vive acá para que no se separen: cada schema declaraba su propio
min_length=1 y nada garantizaba que siguieran iguales — de hecho ya se
habían separado, el rechazo subió a 20 y pedir-cambios quedó en 1.
"""

# El texto es lo único que el autor recibe como explicación. Con el
# min_length=1 anterior, "no" era válido. 20 caracteres no garantizan
# calidad, pero descartan el monosílabo y obligan a escribir una frase.
#
# Mismo número para las tres decisiones a propósito: si pedir cambios fuera
# más laxo que rechazar, el caso donde el autor MÁS necesita saber qué hacer
# sería el peor explicado.
MIN_EXPLICACION = 20

# Nombre anterior, conservado porque revision/schemas.py y comites/schemas.py
# lo importan como el mínimo del motivo de rechazo.
MIN_MOTIVO_RECHAZO = MIN_EXPLICACION

MENSAJE_MOTIVO_CORTO = (
    f"El motivo de rechazo debe tener al menos {MIN_EXPLICACION} caracteres: "
    "es la única explicación que recibe quien propuso la idea."
)

MENSAJE_RETROALIMENTACION_CORTA = (
    f"La retroalimentación debe tener al menos {MIN_EXPLICACION} caracteres: "
    "es lo único que le dice al autor qué tiene que corregir."
)


def _validar_texto_minimo(texto: str, mensaje_error: str) -> str:
    """Devuelve el texto recortado, o lanza HTTPException 400.

    Valida contra el texto YA recortado, no solo con el min_length del
    schema: 20 espacios en blanco cumplen el schema y no explican nada.
    """
    from fastapi import HTTPException

    limpio = (texto or "").strip()
    if len(limpio) < MIN_EXPLICACION:
        raise HTTPException(status_code=400, detail=mensaje_error)
    return limpio


def validar_motivo_rechazo(motivo: str) -> str:
    return _validar_texto_minimo(motivo, MENSAJE_MOTIVO_CORTO)


def validar_retroalimentacion(texto: str) -> str:
    """Pedir cambios: el autor tiene que poder saber qué corregir."""
    return _validar_texto_minimo(texto, MENSAJE_RETROALIMENTACION_CORTA)
