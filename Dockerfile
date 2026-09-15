# Single image for all pipeline steps; each workflow task calls a different subcommand.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY config ./config
# add ".[energy]" to include CodeCarbon energy estimates (bigger image)
RUN pip install .

RUN useradd --uid 1000 --create-home cstwin && mkdir /work && chown cstwin /work
USER 1000

ENTRYPOINT ["cstwin", "--config", "/app/config/pipeline.yaml", "--workdir", "/work"]
CMD ["--help"]
