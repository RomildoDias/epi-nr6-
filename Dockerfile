FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --only-binary=Pillow Pillow==10.3.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copia tudo
COPY app/ ./app/
COPY static/ ./static/
COPY assets/ ./assets/
COPY data/ ./data/

# Garante pastas
RUN mkdir -p data/fichas data/backup data/relatorios assets/qrcodes

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]

