import io
import json
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from comites.models import ComiteIdea
from core.database import get_db
from documentos import schemas
from documentos.archivos import sanitizar_nombre_archivo
from documentos.models import DocumentoGenerado, PermisoDocumentoRol, TipoDocumento
from documentos.pdf import html_a_pdf_bytes
from documentos.plantillas_html import renderizar_documento
from documentos.service import generar_documentos_para_tipos
from ideas.models import EstadoIdea, Idea
from revision.models import HistorialRetroalimentacion, RevisionIdea
from usuarios import models as usuarios_models
from usuarios.dependencies import obtener_usuario_actual

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _obtener_idea(db: Session, idea_id: int) -> Idea:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")
    return idea


def _validar_acceso(db: Session, idea: Idea, usuario: usuarios_models.Usuario) -> None:
    """Acceso de LECTURA (listar/descargar/preview/pdf/zip): admin, el autor,
    el encargado_area asignado como revisor de la idea (mismo criterio que
    _puede_generar, para que pueda ver /pendientes y generar el one-pager
    desde su vista de revisión), o un miembro del CAB correspondiente si la
    idea ya llegó a comité. Ver _puede_generar() para el permiso de generar/
    regenerar, que es más restrictivo que este."""
    if usuario.rol == usuarios_models.RolUsuario.admin:
        return
    if idea.autor_id == usuario.id:
        return

    if usuario.rol == usuarios_models.RolUsuario.encargado_area:
        revision = db.query(RevisionIdea).filter_by(idea_id=idea.id).first()
        if revision is not None and revision.revisor_id == usuario.id:
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


def _puede_generar(db: Session, idea: Idea, usuario: usuarios_models.Usuario) -> bool:
    """Permiso de GENERAR/REGENERAR — más restrictivo que _validar_acceso.

    admin siempre puede. El autor puede generar/regenerar SOLO si la idea
    ya fue ENVIADA (no mientras sigue en borrador, todavía conversando con
    la IA en la entrevista) Y mientras no haya llegado a comité (no existe
    fila en ComiteIdea) — cubre todo el ciclo de revisión, incluyendo
    rondas de "cambios solicitados". En cuanto existe ComiteIdea (sin
    importar si está pendiente, aprobada o rechazada), los documentos
    quedan congelados: ni el autor ni CAB pueden generar más, solo
    ver/descargar lo que ya exista.

    El encargado_area asignado como revisor de la idea tiene el mismo
    permiso que el autor mientras dure la revisión (mismo estado/ComiteIdea
    que arriba) — cubre el caso de que el colaborador no haya generado el
    one-pager antes de enviar. En la práctica queda acotado a los tipos de
    documento que _tipos_permitidos_para_rol ya habilite para encargado_area
    (por semilla, solo "onepager"), sin necesidad de hardcodear el tipo acá.
    """
    if usuario.rol == usuarios_models.RolUsuario.admin:
        return True
    if idea.estado != EstadoIdea.enviada:
        return False

    comite_existe = db.query(ComiteIdea).filter_by(idea_id=idea.id).first() is not None
    if comite_existe:
        return False

    if idea.autor_id == usuario.id:
        return True

    if usuario.rol == usuarios_models.RolUsuario.encargado_area:
        revision = db.query(RevisionIdea).filter_by(idea_id=idea.id).first()
        if revision is not None and revision.revisor_id == usuario.id:
            return True

    return False


def _tipos_permitidos_para_rol(db: Session, rol: usuarios_models.RolUsuario) -> set[TipoDocumento]:
    """Tipos de documento que ese rol puede GENERAR (configurable por admin
    desde ConfiguracionDocumentosView, ver PATCH /documentos/permisos-rol).

    admin no tiene filas en permisos_documentos_rol a propósito: siempre
    puede generar cualquier tipo, sin depender de configuración — mismo
    criterio que _puede_generar() ya usa para el resto de los chequeos.
    """
    if rol == usuarios_models.RolUsuario.admin:
        return set(TipoDocumento)
    filas = db.query(PermisoDocumentoRol).filter_by(rol=rol, permitido=True).all()
    return {f.tipo_documento for f in filas}


def _documentos_desactualizados(db: Session, idea_id: int, documentos: list[DocumentoGenerado]) -> bool:
    """True si existe al menos un documento generado y, DESPUÉS de la
    generación más reciente, hubo una ronda de retroalimentación (la idea
    volvió a revisión con cambios solicitados) — señal de que el
    contenido pudo quedar desactualizado. Solo informativo, no bloquea
    nada ni fuerza regeneración."""
    if not documentos:
        return False

    ultima_generacion = max(d.generado_en for d in documentos)

    revision = db.query(RevisionIdea).filter_by(idea_id=idea_id).first()
    if not revision:
        return False

    ultima_retro = (
        db.query(HistorialRetroalimentacion)
        .filter_by(revision_id=revision.id)
        .order_by(HistorialRetroalimentacion.creada_en.desc())
        .first()
    )
    if not ultima_retro:
        return False

    return ultima_retro.creada_en > ultima_generacion


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

    documentos = _documentos_de_idea(db, idea_id)
    generados = {d.tipo_documento for d in documentos}
    todos = list(TipoDocumento)

    return schemas.PendientesOut(
        generados=[t for t in todos if t in generados],
        pendientes=[t for t in todos if t not in generados],
        puede_generar=_puede_generar(db, idea, usuario_actual),
        documentos_desactualizados=_documentos_desactualizados(db, idea_id, documentos),
        tipos_permitidos_rol=sorted(_tipos_permitidos_para_rol(db, usuario_actual.rol), key=lambda t: t.value),
    )


@router.post("/{idea_id}/generar", response_model=list[schemas.DocumentoGeneradoOut])
def generar(
    idea_id: int,
    payload: schemas.GenerarDocumentosRequest,
    db: Session = Depends(get_db),
    usuario_actual: usuarios_models.Usuario = Depends(obtener_usuario_actual),
):
    if not payload.tipos:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un tipo de documento")

    # Bloquea la fila de Idea (no ComiteIdea: mientras se puede generar,
    # ComiteIdea todavía no existe) para serializar generaciones
    # concurrentes de la misma idea — mismo patrón que criterios/router.py
    # con with_for_update(). El lock se mantiene durante toda la llamada a
    # Claude (potencialmente varios segundos): decisión consciente, el
    # riesgo real de una carrera acá es muy bajo.
    idea = db.query(Idea).filter_by(id=idea_id).with_for_update().first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea no encontrada")

    if not _puede_generar(db, idea, usuario_actual):
        comite_existe = db.query(ComiteIdea).filter_by(idea_id=idea_id).first() is not None
        detalle = (
            "Los documentos ya no se pueden generar ni regenerar: la idea ya está en comité."
            if comite_existe
            else "No tienes permiso para generar documentos de esta idea."
        )
        raise HTTPException(status_code=403, detail=detalle)

    permitidos = _tipos_permitidos_para_rol(db, usuario_actual.rol)
    no_permitidos = [t for t in payload.tipos if t not in permitidos]
    if no_permitidos:
        etiquetas = ", ".join(t.value for t in no_permitidos)
        raise HTTPException(
            status_code=403,
            detail=f"Tu rol no tiene permiso para generar: {etiquetas}",
        )

    existentes = {
        d.tipo_documento.value: d
        for d in db.query(DocumentoGenerado).filter_by(idea_id=idea_id).all()
    }

    nuevos = generar_documentos_para_tipos(
        db, idea, [t.value for t in payload.tipos], existentes
    )
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
