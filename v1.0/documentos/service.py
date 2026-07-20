"""Generación manual de documentos formales para una idea aprobada por CAB.

Llamado desde documentos/router.py:generar, dentro de una transacción con
lock sobre ComiteIdea (ver ese router para el manejo de la condición de
carrera). Genera únicamente los tipos pedidos que todavía no existan —
son inmutables, nunca se regeneran (ver docstring de DocumentoGenerado).
"""

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


def generar_documentos_para_tipos(db: Session, idea: Idea, tipos: list[str]) -> list[DocumentoGenerado]:
    """Genera los documentos de `tipos` (ya filtrados por el caller para
    excluir los que ya existen) en una sola llamada a Claude para todo
    el contenido narrativo — ver core/claude_client.py:generar_contenido_documentos.
    """
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

        documento = DocumentoGenerado(
            idea_id=idea.id,
            tipo_documento=tipo,
            contenido=json.dumps(datos, ensure_ascii=False),
            ruta_archivo=ruta_archivo,
        )
        db.add(documento)
        documentos.append(documento)

    return documentos
