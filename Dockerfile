FROM python:3.14-slim

WORKDIR /app

ARG DART_SASS_VERSION=1.98.0
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && SASS_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x64") \
    && curl -fsSL https://github.com/sass/dart-sass/releases/download/${DART_SASS_VERSION}/dart-sass-${DART_SASS_VERSION}-linux-${SASS_ARCH}.tar.gz \
        | tar -xz -C /usr/local \
    && ln -s /usr/local/dart-sass/sass /usr/local/bin/sass \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY pyproject.toml .
RUN pip install -e ".[dev]"

COPY . .

RUN sass static/css/source/screen.scss static/css/screen.css --style=compressed

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
