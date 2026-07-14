import os
import re

DIRECTORIO_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "documentos")

CARACTERES_PROHIBIDOS_WINDOWS = re.compile(r'[\\/:*?"<>|]')


def ruta_para(idea_id: int, tipo_documento: str) -> str:
    directorio_idea = os.path.join(DIRECTORIO_BASE, str(idea_id))
    os.makedirs(directorio_idea, exist_ok=True)
    return os.path.join(directorio_idea, f"{tipo_documento}.docx")


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
