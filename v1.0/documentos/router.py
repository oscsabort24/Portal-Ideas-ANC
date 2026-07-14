import io
import json
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from comites.models import ComiteIdea
from core.database import get_db
from documentos import schemas
from documentos.archivos import sanitizar_nombre_archivo
from documentos.models import DocumentoGenerado, TipoDocumento
from ideas.models import Idea
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _obtener_idea(db: Session, idea_id: int) -> Idea:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    return idea


def _validar_acceso(db: Session, idea: Idea, usuario: usuarios_models.Usuario) -> None:
    if usuario.rol == usuarios_models.RolUsuario.admin:
        return
    if idea.autor_id == usuario.id:
        return

    comite = db.query(ComiteIdea).filter_by(idea_id=idea.id).first()
    if comite:
        es_miembro = (
            db.query(usuarios_models.MiembroCAB)
            .filter(
                usuarios_models.MiembroCAB.usuario_id == usuario.id,
                usuarios_models.MiembroCAB.tipo_cab == comite.tipo_cab,
            )
            .first()
            is not None
        )
        if es_miembro:
            return

    raise HTTPException(status_code=403, detail="No tienes acceso a los documentos de esta idea")


def _documentos_de_idea(db: Session, idea_id: int) -> list[DocumentoGenerado]:
    documentos = db.query(DocumentoGenerado).filter(DocumentoGenerado.idea_id == idea_id).all()
    if not documentos:
        raise HTTPException(status_code=404, detail="Esta idea todavía no tiene documentos generados")
    return documentos


@router.get("/{idea_id}", response_model=list[schemas.DocumentoGeneradoOut])
def listar_documentos(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)
    documentos = _documentos_de_idea(db, idea_id)

    return [
        schemas.DocumentoGeneradoOut(
            id=d.id,
            idea_id=d.idea_id,
            tipo_documento=d.tipo_documento,
            contenido=json.loads(d.contenido),
            generado_en=d.generado_en,
        )
        for d in documentos
    ]


@router.get("/{idea_id}/{tipo_documento}/descargar")
def descargar_documento(
    idea_id: int,
    tipo_documento: TipoDocumento,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    documento = (
        db.query(DocumentoGenerado)
        .filter_by(idea_id=idea_id, tipo_documento=tipo_documento)
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Este documento no ha sido generado para esta idea")

    nombre_archivo = f"{sanitizar_nombre_archivo(idea.titulo)} - {tipo_documento.value}.docx"
    return FileResponse(
        documento.ruta_archivo,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=nombre_archivo,
    )


@router.post("/{idea_id}/descargar-zip")
def descargar_zip(
    idea_id: int,
    payload: schemas.DescargarZipRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    if not payload.tipos:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un tipo de documento")

    documentos = (
        db.query(DocumentoGenerado)
        .filter(DocumentoGenerado.idea_id == idea_id, DocumentoGenerado.tipo_documento.in_(payload.tipos))
        .all()
    )
    if not documentos:
        raise HTTPException(status_code=404, detail="Ninguno de los documentos solicitados existe para esta idea")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in documentos:
            zf.write(d.ruta_archivo, arcname=f"{d.tipo_documento.value}.docx")
    buffer.seek(0)

    nombre_zip = f"{sanitizar_nombre_archivo(idea.titulo)}.zip"
    # Los headers HTTP son latin-1; un nombre con tildes necesita el parámetro
    # filename* (RFC 6266, UTF-8 percent-encoded) además de un fallback ASCII
    # para clientes que no lo soportan — mismo criterio que FileResponse ya
    # aplica automáticamente en descargar_documento().
    nombre_ascii = nombre_zip.encode("ascii", "ignore").decode("ascii") or "documentos.zip"
    content_disposition = f"attachment; filename=\"{nombre_ascii}\"; filename*=UTF-8''{quote(nombre_zip)}"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": content_disposition},
    )
