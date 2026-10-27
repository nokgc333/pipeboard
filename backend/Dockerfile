FROM python:3.12-slim

WORKDIR /app

COPY requirements-runtime.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements-runtime.lock

COPY app ./app

RUN useradd --system --uid 10001 pipeboard \
    && mkdir -p /app/data /app/uploads \
    && chown -R pipeboard /app/data /app/uploads
USER pipeboard

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["sh", "-c", "python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
