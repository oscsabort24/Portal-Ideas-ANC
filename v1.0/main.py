from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from criterios.router import router as criterios_router
from ideas.router import router as ideas_router
from usuarios.router import router as usuarios_router

app = FastAPI(title="Portafolio de Iniciativas de ANC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios_router)
app.include_router(ideas_router)
app.include_router(criterios_router)

# Routers pendientes a medida que se construyan los módulos:
# from revision.router import router as revision_router
# from clasificacion.router import router as clasificacion_router
# from comites.router import router as comites_router
# from notificaciones.router import router as notificaciones_router
# from documentos.router import router as documentos_router


@app.get("/health")
def health():
    return {"status": "ok"}
