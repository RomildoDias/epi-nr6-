FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instala Pillow com wheel pré-compilada (não compila do fonte)
RUN pip install --upgrade pip && \
    pip install --only-binary=Pillow Pillow==10.3.0 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/fichas data/backup data/relatorios assets/qrcodes static

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
