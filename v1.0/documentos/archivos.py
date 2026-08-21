import os
import re
from pathlib import Path

DIRECTORIO_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documentos")
_DIRECTORIO_BASE_RESUELTO = Path(DIRECTORIO_BASE).resolve()

CARACTERES_PROHIBIDOS_WINDOWS = re.compile(r'[\\/:*?"<>|]')


def ruta_para(idea_id: int, tipo_documento: str) -> str:
    directorio_idea = os.path.join(DIRECTORIO_BASE, str(idea_id))
    os.makedirs(directorio_idea, exist_ok=True)
    return os.path.join(directorio_idea, f"{tipo_documento}.docx")


def ruta_dentro_de_uploads(ruta_archivo: str) -> Path:
    """Defensa en profundidad para descargar_documento/descargar_pdf: hoy
    `ruta_archivo` viene siempre de la base (nunca de input directo de
    usuario), generada únicamente por ruta_para() de acá arriba — así que
    no es explotable hoy. Pero es una dependencia implícita: si el
    mecanismo de generación cambia en el futuro y `ruta_archivo` se vuelve
    parcialmente derivable de input de usuario, servir el archivo sin este
    chequeo sería path traversal (ej. "../../.env"). Resuelve la ruta
    absoluta y confirma que quede DENTRO de DIRECTORIO_BASE antes de
    devolverla; lanza ValueError si no.

    is_relative_to (no startswith de strings) evita el falso positivo
    clásico de comparar prefijos de string (ej. ".../uploads/documentos-evil"
    empieza con ".../uploads/documentos" como string pero no está dentro
    del directorio)."""
    resuelta = Path(ruta_archivo).resolve()
    if not resuelta.is_relative_to(_DIRECTORIO_BASE_RESUELTO):
        raise ValueError(f"ruta_archivo fuera del directorio de uploads esperado: {ruta_archivo!r}")
    return resuelta


def sanitizar_nombre_archivo(titulo: str) -> str:
    """Convierte un título de idea en un nombre de archivo válido en Windows.

    Reemplaza los 8 caracteres prohibidos (\\ / : * ? " < > |), colapsa
    espacios y recorta espacios/puntos finales (Windows no permite que un
    nombre de archivo termine en ninguno de los dos). Nunca devuelve
    vacío — cae a "idea" si el título queda en blanco tras sanitizar.
    """
    limpio = CARACTERES_PROHIBIDOS_WINDOWS.sub("_", titulo)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    limpio = limpio.rstrip(". ")
    return limpio[:150] or "idea"
