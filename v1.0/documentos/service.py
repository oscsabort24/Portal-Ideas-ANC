"""Generación de los 6 documentos formales al aprobar una idea por CAB.

Llamado desde comites/router.py:aprobar, dentro de la misma transacción.
Genera los 6 documentos juntos, una sola vez — no hay regeneración
on-demand ni edición posterior (ver docstring de DocumentoGenerado).
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from documentos.archivos import ruta_para
from documentos.generadores import GENERADORES
from documentos.models import DocumentoGenerado, TipoDocumento
from ideas.models import Idea, MensajeEntrevista
from core.claude_client import generar_contenido_documento


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


def generar_documentos_para_idea(db: Session, idea: Idea) -> list[DocumentoGenerado]:
    contexto_estructural = _contexto_estructural(idea)
    historial = _historial_para_ia(db, idea.id)

    documentos = []
    for tipo in TipoDocumento:
        contenido_narrativo = generar_contenido_documento(historial, tipo.value)
        datos = {**contexto_estructural, **contenido_narrativo}

        ruta_archivo = ruta_para(idea.id, tipo.value)
        GENERADORES[tipo.value](datos, ruta_archivo)

        documento = DocumentoGenerado(
            idea_id=idea.id,
            tipo_documento=tipo,
            contenido=json.dumps(datos, ensure_ascii=False),
            ruta_archivo=ruta_archivo,
        )
        db.add(documento)
        documentos.append(documento)

    return documentos
