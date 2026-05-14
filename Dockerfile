FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]

# FROM python:3.11-slim

# # Directorio de trabajo dentro del contenedor
# WORKDIR /app

# # Copiar archivo de dependencias
# COPY requirements.txt .

# # Instalar dependencias Python
# RUN pip install --no-cache-dir -r requirements.txt

# # Instalar Chromium para Playwright
# RUN playwright install chromium

# # Instalar dependencias Linux necesarias para Chromium
# RUN apt-get update && apt-get install -y \
#     wget \
#     curl \
#     gnupg \
#     libnss3 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libcups2 \
#     libxkbcommon0 \
#     libxcomposite1 \
#     libxdamage1 \
#     libxrandr2 \
#     libgbm1 \
#     libasound2 \
#     libpangocairo-1.0-0 \
#     libgtk-3-0 \
#     libxshmfence1 \
#     fonts-liberation \
#     libappindicator3-1 \
#     xdg-utils \
#     && rm -rf /var/lib/apt/lists/*

# # Copiar todo el proyecto al contenedor
# COPY . .

# # Exponer puerto
# EXPOSE 8000

# # Ejecutar FastAPI con Gunicorn + Uvicorn
# CMD gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT