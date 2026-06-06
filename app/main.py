import os
import secrets
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.routes import router
from app.db.database import init_db
from app.core.config import settings
from app.core.limiter import limiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 16:
        key_file = settings.DATA_DIR / ".secret_key"
        if key_file.exists():
            settings.SECRET_KEY = key_file.read_text().strip()
            logger.info("SECRET_KEY carregada do disco persistente")
        else:
            settings.SECRET_KEY = secrets.token_hex(32)
            key_file.write_text(settings.SECRET_KEY)
            logger.info("SECRET_KEY gerada e persistida em disco")
    # Cria pastas necessárias
    for d in [settings.DATA_DIR, settings.FICHAS_DIR,
              settings.QRCODES_DIR, settings.DATA_DIR / "relatorios"]:
        d.mkdir(parents=True, exist_ok=True)
    # Inicializa banco e seed
    try:
        init_db()
        logger.info("✓ Banco de dados inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
    yield


app = FastAPI(
    title="Controle EPI NR-6",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse({"detail": "Erro interno do servidor"}, status_code=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "https://epi-nr6-1-34ib.onrender.com")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(router, prefix="/api")

# Serve o frontend — tenta encontrar static em vários lugares
_static = None
for _candidate in [
    Path(__file__).parent.parent / "static",
    Path("/app/static"),
    Path("static"),
]:
    if (_candidate / "index.html").exists():
        _static = _candidate
        break

if _static:
    logger.info(f"✓ Frontend em: {_static}")

    @app.get("/")
    def index():
        return FileResponse(str(_static / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Não intercepta rotas da API
        if full_path.startswith("api"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = _static / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/")
    def root():
        return {
            "status": "EPI NR-6 API rodando",
            "docs": "/api/docs",
            "login": "POST /api/auth/login",
            "aviso": "Frontend não encontrado — acesse /api/docs"
        }
