# backend/app/core/security.py
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

PERFIS_PERMISSOES = {
    "superadmin": {
        "ver_dashboard","cadastrar_epi","editar_epi","inativar_epi",
        "registrar_entrega","entrada_estoque","ajuste_estoque",
        "ver_relatorios","gerenciar_usuarios","gerenciar_tenants",
        "ver_config","editar_config","backup",
    },
    "admin": {
        "ver_dashboard","cadastrar_epi","editar_epi","inativar_epi",
        "registrar_entrega","entrada_estoque","ajuste_estoque",
        "ver_relatorios","gerenciar_usuarios",
        "ver_config","editar_config","backup",
    },
    "operador": {
        "ver_dashboard","cadastrar_epi","editar_epi",
        "registrar_entrega","entrada_estoque","ajuste_estoque",
        "ver_relatorios",
    },
    "visualizador": {"ver_dashboard","ver_relatorios"},
}

HIERARQUIA_PERFIL = {"visualizador": 0, "operador": 1, "admin": 2, "superadmin": 3}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
        "aud": "epi-web",
        "iss": "epi-web",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
                          audience="epi-web", issuer="epi-web")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token inválido ou expirado")


async def get_current_user(token: str = Depends(oauth2_scheme),
                            db: Session = Depends(get_db)):
    from app.db import models_db
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    jti: str = payload.get("jti")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(models_db.Usuario).filter(
        models_db.Usuario.id == user_id,
        models_db.Usuario.ativo == True
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def require_permission(acao: str):
    """Dependency que verifica permissão."""
    async def checker(current_user=Depends(get_current_user)):
        perms = PERFIS_PERMISSOES.get(current_user.perfil, set())
        if acao not in perms:
            raise HTTPException(status_code=403,
                                detail=f"Sem permissão para: {acao}")
        return current_user
    return checker


def tenant_filter(query, model, current_user):
    """Aplica filtro de tenant na query SQLAlchemy."""
    if current_user.perfil == "superadmin":
        return query
    return query.filter(model.tenant_id == current_user.tenant_id)
