FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# The host image is CPU-only. Preinstall CPU wheels so the broad runtime
# requirements do not resolve to CUDA/NVIDIA packages in production.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
      "torch==2.8.0+cpu" "torchvision==0.23.0+cpu" \
 && pip install --no-cache-dir -r requirements.txt

COPY . .
COPY data/demo_dossier /opt/eurosetu-demo
ENV EUROSETU_DEMO_FIXTURES_PATH=/opt/eurosetu-demo

RUN useradd -r -u 10001 eurosetu \
 && mkdir -p /app/data \
 && chown -R eurosetu:eurosetu /app
USER eurosetu

# Cloud Run / App Runner inject PORT. Cloudflare Tunnel and Compose leave it
# unset, so default to 8000.
ENV PORT=8000
EXPOSE 8000

# Mount a volume at /app/data to keep the SQLite database across restarts.
# See docs/DEPLOY_CLOUDFLARE.md, docs/DEPLOY_GOOGLE_CLOUD.md and docs/DEPLOY_AWS.md.
ENV EUROSETU_DB_PATH=/app/data/eurosetu.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request,sys; req=urllib.request.Request('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health/ready',headers={'Host':os.getenv('EUROSETU_APP_HOST','app.eurosetu.trade')}); sys.exit(0 if urllib.request.urlopen(req,timeout=4).status==200 else 1)"

CMD ["sh","-c","exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
