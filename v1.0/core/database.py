import pyodbc
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _configurar_decoding_pyodbc(dbapi_connection, connection_record):
    """La base usa collation SQL_Latin1_General_CP1_CI_AS (CP1252), pero
    pyodbc asume UTF-8 al decodificar columnas SQL_CHAR (varchar) por
    defecto. Sin esto, cualquier acento/ñ leído desde varchar sale
    corrupto (ej. "Saborío" -> "Sabor�o"), aunque los bytes en disco
    estén correctamente almacenados en CP1252 — confirmado con
    CONVERT(VARBINARY, ...) contra la BD real.
    """
    dbapi_connection.setdecoding(pyodbc.SQL_CHAR, encoding="cp1252")
    dbapi_connection.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-16le")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
