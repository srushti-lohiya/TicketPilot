FROM python:3.13.4-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DB_PATH=/data/ticketpilot.db
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
# Full local image retains dashboard/optional LLM support. Render uses requirements-render.txt.
COPY requirements.txt requirements-render.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-render.txt
COPY . .
RUN mkdir -p /data && DEMO_MODE=0 RETRIEVAL_BACKEND=tfidf python scripts/check_runtime.py
# Existing model is copied, never trained or downloaded during build/startup.
EXPOSE 8000
CMD ["sh", "scripts/start_render.sh"]
