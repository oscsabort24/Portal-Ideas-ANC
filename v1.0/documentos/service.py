"""Generación manual de documentos formales para una idea.

Llamado desde documentos/router.py:generar, dentro de una transacción con
lock sobre Idea (ver ese router para el manejo de la condición de carrera).
Mientras la idea no haya llegado a comité (no existe ComiteIdea), el autor
puede generar tipos nuevos Y regenerar tipos que ya existían — ver
documentos/router.py:_puede_generar. Una vez que existe ComiteIdea, los
documentos quedan congelados (esta función deja de poder ejecutarse para
esa idea, el gate está en el router)."""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from documentos.archivos import ruta_para
from documentos.generadores import GENERADORES
from documentos.models import DocumentoGenerado
from ideas.models import Idea, MensajeEntrevista
from core.claude_client import generar_contenido_documentos


def _contexto_estructural(idea: Idea) -> dict:
    autor = idea.autor
    return {
        "nombre_proyecto": idea.titulo,
        "titulo": idea.titulo,
        "area_solicitante": autor.departamento.nombre if autor.departamento else "No especificada",
        "solicitante": autor.nombre or "Participante",
        "fecha_emision": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "programa": "Transformación Digital",
        "procedimiento_sig": "No existe",
    }


def _historial_para_ia(db: Session, idea_id: int) -> list[dict]:
    mensajes = (
        db.query(MensajeEntrevista)
        .filter(MensajeEntrevista.idea_id == idea_id)
        .order_by(MensajeEntrevista.orden)
        .all()
    )
    return [{"role": m.rol.value, "content": m.contenido} for m in mensajes]


def generar_documentos_para_tipos(
    db: Session,
    idea: Idea,
    tipos: list[str],
    existentes: dict[str, DocumentoGenerado] | None = None,
) -> list[DocumentoGenerado]:
    """Genera (o regenera) los documentos de `tipos` en una sola llamada a
    Claude para todo el contenido narrativo — ver
    core/claude_client.py:generar_contenido_documentos.

    `existentes` mapea tipo_documento.value -> fila ya existente para esta
    idea (si la hay). Si un tipo pedido ya existe, se actualiza esa MISMA
    fila (contenido/ruta_archivo/generado_en) en vez de crear una nueva —
    `ruta_para()` devuelve un path determinístico por (idea_id, tipo), así
    que el .docx en disco se sobreescribe solo al volver a generarlo.
    """
    existentes = existentes or {}
    if not tipos:
        return []

    contexto_estructural = _contexto_estructural(idea)
    historial = _historial_para_ia(db, idea.id)
    contenido_por_tipo = generar_contenido_documentos(historial, tipos)

    documentos = []
    for tipo in tipos:
        datos = {**contexto_estructural, **contenido_por_tipo.get(tipo, {})}

        ruta_archivo = ruta_para(idea.id, tipo)
        GENERADORES[tipo](datos, ruta_archivo)

        documento_existente = existentes.get(tipo)
        if documento_existente:
            documento_existente.contenido = json.dumps(datos, ensure_ascii=False)
            documento_existente.ruta_archivo = ruta_archivo
            documento_existente.generado_en = datetime.now(timezone.utc)
            documentos.append(documento_existente)
        else:
            documento = DocumentoGenerado(
                idea_id=idea.id,
                tipo_documento=tipo,
                contenido=json.dumps(datos, ensure_ascii=False),
                ruta_archivo=ruta_archivo,
            )
            db.add(documento)
            documentos.append(documento)

    return documentos
