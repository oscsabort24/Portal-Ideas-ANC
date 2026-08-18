import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clasificacion.router import router as clasificacion_router
from comites.router import router as comites_router
from core.config import settings
from criterios.router import router as criterios_router
from documentos.router import router as documentos_router
from ideas.router import router as ideas_router
from notificaciones.router import router as notificaciones_router
from permisos.router import router as permisos_router, router_publico as permisos_publico_router
from revision.router import router as revision_router
from trazabilidad.router import router as trazabilidad_router
from usuarios.router import router as usuarios_router

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Portafolio de Iniciativas de ANC")


@app.on_event("startup")
def _log_config_efectiva() -> None:
    """settings = Settings() se instancia UNA sola vez al importar
    core/config.py — si .env cambia después (ej. se activa la API real de
    Claude), un proceso ya corriendo NO se entera hasta reiniciarse. Este
    log hace explícito en cada arranque qué configuración quedó cargada en
    memoria, para no volver a confundir "el .env dice X" con "el proceso
    vivo realmente está usando X" (nos pasó con CLAUDE_STUB_MODE)."""
    estado_key = "presente" if settings.claude_api_key else "AUSENTE"
    logger.warning(
        "Config efectiva de este proceso: CLAUDE_STUB_MODE=%s | CLAUDE_API_KEY=%s | "
        "CLAUDE_MODEL=%s | CORS_ALLOWED_ORIGINS=%s",
        settings.claude_stub_mode,
        estado_key,
        settings.claude_model,
        settings.cors_allowed_origins_list,
    )
    if settings.claude_stub_mode:
        logger.warning(
            "MODO STUB ACTIVO: la entrevista con la IA usará respuestas simuladas, "
            "no se llamará a la API real de Anthropic."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios_router)
app.include_router(ideas_router)
app.include_router(criterios_router)
app.include_router(revision_router)
app.include_router(clasificacion_router)
app.include_router(comites_router)
app.include_router(notificaciones_router)
app.include_router(documentos_router)
app.include_router(permisos_router)
app.include_router(permisos_publico_router)
app.include_router(trazabilidad_router)

if settings.entorno == "development":
    from core.dev_router import router as dev_router

    logger.warning("ENTORNO=development: /auth/dev-login está activo (accesos rápidos de prueba)")
    app.include_router(dev_router)


@app.get("/health")
def health():
    return {"status": "ok"}
