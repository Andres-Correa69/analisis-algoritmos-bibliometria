# Imagen única: compila la interfaz (Node) y la sirve junto con la API (Python).

# ---------- Etapa 1: build del frontend ----------
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- Etapa 2: API + archivos estáticos ----------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    PORT=8000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 1000 app
COPY bibliometria/ ./bibliometria/
COPY data/ ./data/
# El informe en PDF es opcional: el patrón [f] evita que la construcción falle si no existe.
COPY main.py Informe_Final_Analisis_Algoritmos.pd[f] ./
COPY --from=frontend /app/frontend/dist ./frontend/dist
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
# --proxy-headers: respeta X-Forwarded-* cuando la app está detrás del proxy inverso (Caddy).
CMD ["sh", "-c", "uvicorn bibliometria.api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
