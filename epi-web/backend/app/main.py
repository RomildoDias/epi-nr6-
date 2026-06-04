# backend/app/main.py
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.routes import router
from app.db.database import init_db
from app.core.config import settings
from app.core.limiter import limiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Controle EPI NR-6",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})


# Serve arquivos estáticos do frontend (build do React)
_frontend = Path(__file__).parent.parent / "static"
if _frontend.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve o React SPA para todas as rotas não-API."""
        index = _frontend / "index.html"
        return FileResponse(str(index))


@app.on_event("startup")
def startup():
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 16:
        logger.warning("SECRET_KEY não configurada ou muito curta! Gerando chave temporária.")
        import secrets
        settings.SECRET_KEY = secrets.token_hex(32)
    # Garante pastas
    for d in [settings.DATA_DIR, settings.FICHAS_DIR,
              settings.QRCODES_DIR, settings.DATA_DIR / "relatorios"]:
        d.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Banco de dados inicializado")
    logger.info("API rodando em http://0.0.0.0:8000")
    logger.info("Documentação em http://0.0.0.0:8000/api/docs")
