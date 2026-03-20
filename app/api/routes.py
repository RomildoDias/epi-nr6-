@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Diagnóstico — verifica banco e cria admin se não existir."""
    from app.db.models_db import Usuario
    from app.core.security import hash_password
    import uuid

    try:
        # Tenta contar usuários
        total = db.query(Usuario).count()

        # Se não tiver nenhum, cria o admin agora
        if total == 0:
            db.add(Usuario(
                id=str(uuid.uuid4()),
                nome="Administrador",
                login="admin",
                senha_hash=hash_password("admin123"),
                perfil="superadmin",
                tenant_id=None,
                ativo=True,
            ))
            db.commit()
            return {"status": "ok", "usuarios": 1, "criado": "admin/admin123"}

        return {"status": "ok", "usuarios": total}

    except Exception as e:
        return {"status": "erro", "detalhe": str(e)}
```
