FROM python:3.13.9-slim@sha256:326df678c20c78d465db501563f3492d17c42a4afe33a1f2bf5406a1d56b0e86

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY currency/pyproject.toml ./currency/pyproject.toml
COPY currency/src ./currency/src
COPY policy/pyproject.toml ./policy/pyproject.toml
COPY policy/src ./policy/src
RUN pip install --no-cache-dir ./currency ./policy

USER 65532:65532
EXPOSE 8000
CMD ["python", "-m", "currency_mcp"]
