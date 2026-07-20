import io
import json
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from comites.models import ComiteIdea, EstadoComite
from core.database import get_db
from documentos import schemas
from documentos.archivos import sanitizar_nombre_archivo
from documentos.models import DocumentoGenerado, TipoDocumento
from documentos.pdf import html_a_pdf_bytes
from documentos.plantillas_html import renderizar_documento
from documentos.service import generar_documentos_para_tipos
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
    return db.query(DocumentoGenerado).filter(DocumentoGenerado.idea_id == idea_id).all()


@router.get("/{idea_id}", response_model=list[schemas.DocumentoGeneradoOut])
def listar_documentos(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)
    # Con generación manual, "aprobada por el CAB pero sin documentos
    # todavía" es un estado normal y esperado — ya no es un 404, es una
    # lista vacía (el frontend usa /pendientes para decidir qué ofrecer).
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


def _obtener_documento(db: Session, idea_id: int, tipo_documento: TipoDocumento) -> DocumentoGenerado:
    documento = (
        db.query(DocumentoGenerado)
        .filter_by(idea_id=idea_id, tipo_documento=tipo_documento)
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Este documento no ha sido generado para esta idea")
    return documento


@router.get("/{idea_id}/{tipo_documento}/preview", response_class=HTMLResponse)
def preview_documento(
    idea_id: int,
    tipo_documento: TipoDocumento,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    documento = _obtener_documento(db, idea_id, tipo_documento)
    html = renderizar_documento(tipo_documento.value, json.loads(documento.contenido))
    return HTMLResponse(content=html)


@router.get("/{idea_id}/{tipo_documento}/pdf")
def descargar_pdf(
    idea_id: int,
    tipo_documento: TipoDocumento,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    documento = _obtener_documento(db, idea_id, tipo_documento)
    html = renderizar_documento(tipo_documento.value, json.loads(documento.contenido))
    pdf_bytes = html_a_pdf_bytes(html)

    nombre_pdf = f"{sanitizar_nombre_archivo(idea.titulo)} - {tipo_documento.value}.pdf"
    nombre_ascii = nombre_pdf.encode("ascii", "ignore").decode("ascii") or "documento.pdf"
    content_disposition = f"attachment; filename=\"{nombre_ascii}\"; filename*=UTF-8''{quote(nombre_pdf)}"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition},
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


@router.get("/{idea_id}/pendientes", response_model=schemas.PendientesOut)
def pendientes(
    idea_id: int,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    comite = db.query(ComiteIdea).filter_by(idea_id=idea_id).first()
    if not comite or comite.estado != EstadoComite.aprobada:
        # Todavía no aplica generar nada — ni "generados" ni "pendientes"
        # tienen sentido antes de que el CAB apruebe.
        return schemas.PendientesOut(generados=[], pendientes=[])

    generados = {d.tipo_documento for d in _documentos_de_idea(db, idea_id)}
    todos = list(TipoDocumento)
    return schemas.PendientesOut(
        generados=[t for t in todos if t in generados],
        pendientes=[t for t in todos if t not in generados],
    )


@router.post("/{idea_id}/generar", response_model=list[schemas.DocumentoGeneradoOut])
def generar(
    idea_id: int,
    payload: schemas.GenerarDocumentosRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    idea = _obtener_idea(db, idea_id)
    _validar_acceso(db, idea, usuario_actual)

    if not payload.tipos:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un tipo de documento")

    # Bloquea la fila de ComiteIdea de esta idea (única por idea_id) para
    # serializar generaciones concurrentes del mismo tipo — mismo patrón
    # que criterios/router.py con with_for_update(). El lock se mantiene
    # durante toda la llamada a Claude (potencialmente varios segundos):
    # es una decisión consciente. El riesgo real de que dos personas
    # disparen "generar" para la misma idea casi al mismo tiempo es muy
    # bajo, y no se justifica la complejidad de partir esto en 2
    # transacciones (reservar tipos primero, generar después) solo para
    # ese caso extremo.
    comite = (
        db.query(ComiteIdea)
        .filter_by(idea_id=idea_id)
        .with_for_update()
        .first()
    )
    if not comite:
        raise HTTPException(status_code=404, detail="No existe registro de comité para esta idea")
    if comite.estado != EstadoComite.aprobada:
        raise HTTPException(status_code=400, detail="Esta idea todavía no fue aprobada por el CAB")

    existentes = {
        d.tipo_documento.value
        for d in db.query(DocumentoGenerado.tipo_documento).filter_by(idea_id=idea_id).all()
    }
    faltantes = [t.value for t in payload.tipos if t.value not in existentes]

    if not faltantes:
        # Todo lo pedido ya existía (inmutable, no se regenera) — nada que hacer.
        db.commit()
        return []

    nuevos = generar_documentos_para_tipos(db, idea, faltantes)
    db.commit()
    for d in nuevos:
        db.refresh(d)

    return [
        schemas.DocumentoGeneradoOut(
            id=d.id,
            idea_id=d.idea_id,
            tipo_documento=d.tipo_documento,
            contenido=json.loads(d.contenido),
            generado_en=d.generado_en,
        )
        for d in nuevos
    ]
