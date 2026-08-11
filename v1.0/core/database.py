import pyodbc
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _configurar_decoding_pyodbc(dbapi_connection, connection_record):
    """La base usa collation SQL_Latin1_General_CP1_CI_AS (CP1252), pero
    pyodbc asume UTF-8 al decodificar/codificar por defecto. Sin esto,
    cualquier acento/ñ leído desde varchar sale corrupto (ej. "Saborío"
    -> "Sabor�o"), y cualquier carácter fuera de CP1252 (ej. "→") escrito
    hacia una columna nvarchar lanza UnicodeEncodeError, porque pyodbc
    reutiliza la codificación de SQL_CHAR también para la escritura de
    parámetros SQL_WCHAR si no se configura setencoding() explícitamente.
    """
    dbapi_connection.setdecoding(pyodbc.SQL_CHAR, encoding="cp1252")
    dbapi_connection.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-16le")
    dbapi_connection.setencoding(encoding="cp1252", ctype=pyodbc.SQL_CHAR)
    dbapi_connection.setencoding(encoding="utf-16le", ctype=pyodbc.SQL_WCHAR)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
