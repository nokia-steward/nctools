# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build
RUN pip install --no-cache-dir build
COPY pyproject.toml README.md LICENSE requirements.txt ./
COPY src ./src
RUN python -m build -w

FROM ${PYTHON_IMAGE} AS runtime
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl "netconf-tools[yaml]" && rm /tmp/*.whl
USER app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.source=https://github.com/nokia-steward/netconf-tools

FROM runtime AS ncproxy
EXPOSE 830
ENTRYPOINT ["ncproxy"]
