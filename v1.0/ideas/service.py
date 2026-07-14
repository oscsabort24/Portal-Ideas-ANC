from sqlalchemy import func
from sqlalchemy.orm import Session

from ideas.models import MensajeEntrevista


def siguiente_orden(db: Session, idea_id: int) -> int:
    maximo = db.query(func.max(MensajeEntrevista.orden)).filter(
        MensajeEntrevista.idea_id == idea_id
    ).scalar()
    return (maximo or 0) + 1
