FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system signalgraph && useradd --system --gid signalgraph --home-dir /app signalgraph
WORKDIR /app

COPY pyproject.toml alembic.ini requirements.lock requirements-build.lock ./
COPY app ./app
COPY migrations ./migrations
RUN pip install --require-hashes -r requirements-build.lock -r requirements.lock \
    && pip install --no-deps --no-build-isolation . \
    && pip check

USER signalgraph
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
