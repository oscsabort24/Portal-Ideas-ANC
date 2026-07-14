import os
import uuid

from fastapi import HTTPException, UploadFile

EXTENSIONES_PERMITIDAS = {".docx", ".pdf"}

DIRECTORIO_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "criterios")


def validar_extension(archivo: UploadFile) -> str:
    _, extension = os.path.splitext(archivo.filename or "")
    extension = extension.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido ({extension or 'sin extensión'}). Solo se aceptan .docx y .pdf",
        )
    return extension


def guardar_archivo(archivo: UploadFile, tipo: str, version: int, extension: str) -> str:
    directorio_tipo = os.path.join(DIRECTORIO_BASE, tipo)
    os.makedirs(directorio_tipo, exist_ok=True)

    nombre_unico = f"v{version}_{uuid.uuid4().hex[:8]}{extension}"
    ruta_absoluta = os.path.join(directorio_tipo, nombre_unico)

    with open(ruta_absoluta, "wb") as destino:
        destino.write(archivo.file.read())

    return ruta_absoluta


def borrar_archivo(ruta_archivo: str) -> None:
    if os.path.exists(ruta_archivo):
        os.remove(ruta_archivo)
