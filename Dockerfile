FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml main.py ./
COPY apps ./apps
COPY shipster ./shipster

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir . "uvicorn[standard]"

EXPOSE 8000

CMD ["python", "main.py"]
