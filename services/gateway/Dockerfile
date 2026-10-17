FROM python:3.13.9-slim@sha256:326df678c20c78d465db501563f3492d17c42a4afe33a1f2bf5406a1d56b0e86

WORKDIR /app
COPY services/gateway/pyproject.toml ./pyproject.toml
COPY services/gateway/app ./app
COPY services/gateway/alembic.ini ./alembic.ini
COPY services/gateway/alembic ./alembic
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 gateway
USER 10001

EXPOSE 8000
CMD ["python", "-m", "app.main"]
