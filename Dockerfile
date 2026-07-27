FROM mirror.gcr.io/library/python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="hbg-free-material" \
      org.opencontainers.image.source="https://github.com/Mr-funny/hbg-free-material" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HBG_MATERIAL_DOWNLOAD_DIR=/downloads

WORKDIR /app

COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src

RUN python -m pip install --no-cache-dir . \
    && mkdir -p /downloads

VOLUME ["/downloads"]

ENTRYPOINT ["hbg-free-material"]
CMD ["--help"]
