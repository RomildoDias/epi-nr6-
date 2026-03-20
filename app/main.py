from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.routes import router
from app.db.database import init_db
from app.core.config import settings

app = FastAPI(
    title="Controle EPI NR-6",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve o frontend React (pasta static na raiz)
_static = Path(__file__).parent.parent / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api"):
            return None
        index = _static / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/")
    def root():
        return {"status": "EPI NR-6 API running", "docs": "/api/docs"}


@app.on_event("startup")
def startup():
    for d in [settings.DATA_DIR, settings.FICHAS_DIR,
              settings.QRCODES_DIR, settings.DATA_DIR / "relatorios"]:
        d.mkdir(parents=True, exist_ok=True)
    init_db()
    print("✓ Sistema iniciado")
    print(f"✓ Docs: /api/docs")
