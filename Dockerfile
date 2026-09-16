# One container serves both halves: the page at / and the API at /compare.
FROM python:3.11-slim

# pdfplumber needs no system libs beyond these for the PDFs we handle.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libjpeg62-turbo zlib1g \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so a code change does not re-install them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY web/ ./web/
COPY demo/ ./demo/

# Render supplies $PORT. The default keeps `docker run -p 8000:8000` working locally.
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000

# Never bake the key in. It arrives from the host's environment at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
