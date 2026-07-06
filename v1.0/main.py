from fastapi import FastAPI

from usuarios.router import router as usuarios_router

app = FastAPI(title="Portafolio de Iniciativas de ANC")

app.include_router(usuarios_router)

# Routers pendientes a medida que se construyan los módulos:
# from ideas.router import router as ideas_router
# from revision.router import router as revision_router
# from clasificacion.router import router as clasificacion_router
# from comites.router import router as comites_router
# from notificaciones.router import router as notificaciones_router
# from documentos.router import router as documentos_router


@app.get("/health")
def health():
    return {"status": "ok"}
