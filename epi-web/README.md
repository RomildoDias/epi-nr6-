# Controle EPI NR-6 — Versão Web

Sistema multi-tenant para controle de EPIs, acessível por qualquer navegador.

---

## Arquitetura

```
Navegador (qualquer PC/celular)
        ↓ HTTPS
    Nginx (porta 80/443)
        ↓
    FastAPI + Python (porta 8000)
        ↓
    PostgreSQL (banco de dados)
```

---

## Deploy em 5 passos (VPS Linux)

### 1. Contratar VPS
- **Hostinger KVM 2** — R$ 40/mês (2 GB RAM, 20 GB SSD) ✓
- **DigitalOcean Droplet** — ~R$ 50/mês
- Sistema operacional: **Ubuntu 22.04**

### 2. Instalar Docker no VPS

```bash
# Conecte via SSH
ssh root@IP_DO_VPS

# Instala Docker + Compose
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin
```

### 3. Enviar os arquivos para o VPS

```bash
# Do seu PC local, envie a pasta epi-web para o VPS
scp -r epi-web/ root@IP_DO_VPS:/opt/epi-web
```

### 4. Configurar e subir

```bash
cd /opt/epi-web

# IMPORTANTE: troque a SECRET_KEY no docker-compose.yml
nano docker-compose.yml
# Altere: SECRET_KEY: COLOQUE_UMA_CHAVE_ALEATORIA_LONGA_AQUI

# Sobe tudo (banco + backend + nginx)
docker compose up -d

# Acompanha os logs
docker compose logs -f backend
```

### 5. Acessar

Abra o navegador e acesse `http://IP_DO_VPS`

```
Login:  admin
Senha:  admin123
```

**Troque a senha imediatamente** em Administração → Usuários → Editar.

---

## SSL grátis com Let's Encrypt (HTTPS)

```bash
# Instala certbot
apt install -y certbot

# Gera certificado (substitua pelo seu domínio)
certbot certonly --standalone -d seudominio.com.br

# Copia os certificados
cp /etc/letsencrypt/live/seudominio.com.br/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/seudominio.com.br/privkey.pem   nginx/certs/

# Descomenta o bloco HTTPS no nginx/nginx.conf
nano nginx/nginx.conf

# Reinicia o nginx
docker compose restart nginx
```

---

## Operação cotidiana

```bash
# Parar o sistema
docker compose down

# Atualizar o código
git pull   # ou envie novamente via scp
docker compose up -d --build

# Ver logs do backend
docker compose logs -f backend

# Backup do banco de dados
docker compose exec db pg_dump -U epi_user epi_db > backup_$(date +%Y%m%d).sql
```

---

## Estrutura de arquivos

```
epi-web/
  backend/
    app/
      api/routes.py         ← Todos os endpoints REST
      core/config.py        ← Configurações (env vars)
      core/security.py      ← JWT + permissões
      db/models_db.py       ← Tabelas SQLAlchemy
      db/database.py        ← Conexão PostgreSQL
      db/schemas.py         ← Schemas Pydantic
      services/rules.py     ← Regras de negócio NR-6
      services/pdf_ficha.py ← Geração Ficha de Entrega
      services/pdf_report.py← Relatórios em PDF
      main.py               ← App FastAPI
    static/index.html       ← Frontend React (single file)
    requirements.txt
    Dockerfile
    data/                   ← PDFs e fichas gerados
    assets/                 ← QR codes
  nginx/nginx.conf
  docker-compose.yml
```

---

## Credenciais padrão e hierarquia

| Perfil | O que pode fazer |
|--------|-----------------|
| `superadmin` | Tudo — gerencia todos os estados |
| `admin` | Tudo no próprio estado — cria usuários |
| `operador` | Cadastra EPIs, registra entregas, movimenta estoque |
| `visualizador` | Somente leitura |

---

## API REST — Documentação interativa

Com o sistema rodando, acesse:
```
http://IP_DO_VPS/api/docs
```
Interface Swagger com todos os endpoints documentados e testáveis.

⚠ Token removido por segurança.
