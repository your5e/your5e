FROM python:3.14-slim AS base
WORKDIR /app

ARG DART_SASS_VERSION=1.98.0
ARG TARGETARCH
ENV DART_SASS_VERSION=${DART_SASS_VERSION} TARGETARCH=${TARGETARCH}
RUN <<EOF
    set -e
    apt-get update
    apt-get install -y --no-install-recommends curl ca-certificates

    # dart-sass
    SASS_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x64")
    SASS_BASE="https://github.com/sass/dart-sass/releases/download"
    SASS_FILE="dart-sass-${DART_SASS_VERSION}-linux-${SASS_ARCH}.tar.gz"
    curl -fsSL "${SASS_BASE}/${DART_SASS_VERSION}/${SASS_FILE}" | tar -xz -C /usr/local
    ln -s /usr/local/dart-sass/sass /usr/local/bin/sass

    # cleanup
    apt-get purge -y curl
    apt-get autoremove -y
    rm -rf /var/lib/apt/lists/*
EOF

EXPOSE 8000

RUN pip install --upgrade pip
COPY pyproject.toml .


# development image
# =================
FROM base AS dev
RUN pip install .[dev]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# production image
# ================
FROM base AS prod
RUN pip install .

COPY manage.py .
COPY api/ api/
COPY campaigns/ campaigns/
COPY config/ config/
COPY help/ help/
COPY notebooks/ notebooks/
COPY static/ static/
COPY templates/ templates/
COPY users/ users/
COPY wikis/ wikis/

RUN sass static/css/source/screen.scss static/css/screen.css --style=compressed
RUN SECRET_KEY=build DB_NAME=x DB_USER=x DB_PASSWORD=x DB_HOST=x DB_PORT=5432 \
        python manage.py collectstatic --no-input

CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload"]
