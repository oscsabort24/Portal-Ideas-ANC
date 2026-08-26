"""Reglas comunes a los DOS puntos de rechazo del sistema.

Una idea puede rechazarse en revisión de área (revision/router.py:rechazar)
o en comité (comites/router.py:rechazar). Los dos casos comparten la misma
exigencia sobre el motivo, y vive acá para que no se separen: hasta ahora
cada schema declaraba su propio min_length=1 y nada garantizaba que
siguieran iguales.
"""

# Un rechazo cierra el camino de la idea y este texto es lo único que el autor
# recibe como explicación. Con el min_length=1 anterior, "no" era un motivo
# válido. 20 caracteres no garantizan calidad, pero descartan el monosílabo y
# obligan a escribir una frase.
MIN_MOTIVO_RECHAZO = 20

MENSAJE_MOTIVO_CORTO = (
    f"El motivo de rechazo debe tener al menos {MIN_MOTIVO_RECHAZO} caracteres: "
    "es la única explicación que recibe quien propuso la idea."
)


def validar_motivo_rechazo(motivo: str) -> str:
    """Devuelve el motivo recortado, o lanza HTTPException 400.

    Se valida contra el texto YA recortado, no solo con el min_length del
    schema: 20 espacios en blanco cumplen el schema y no explican nada.
    """
    from fastapi import HTTPException

    limpio = (motivo or "").strip()
    if len(limpio) < MIN_MOTIVO_RECHAZO:
        raise HTTPException(status_code=400, detail=MENSAJE_MOTIVO_CORTO)
    return limpio
