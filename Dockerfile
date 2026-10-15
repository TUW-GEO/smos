# Image with the smos package and the lftp program (required for downloads).
# Usage, e.g.: docker run --rm -v /data:/data <image> smos l3 update_img /data/smos_l3
# The container runs as user `smos` (uid 1000), pass e.g.
# `--user $(id -u):$(id -g)` to read/write mounted data as your own user.
ARG PYTHON_VERSION=3.14

# Build the wheel in a separate stage, git is needed to derive the version
# (setuptools_scm), but is not part of the final image.
FROM python:${PYTHON_VERSION}-slim AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:${PYTHON_VERSION}-slim
LABEL org.opencontainers.image.source="https://github.com/TUW-GEO/smos" \
      org.opencontainers.image.description="SMOS soil moisture data download, readers and time series conversion" \
      org.opencontainers.image.licenses="MIT"
RUN apt-get update \
    && apt-get install -y --no-install-recommends lftp ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Don't run as root
RUN useradd --create-home --uid 1000 smos
USER smos
WORKDIR /home/smos

CMD ["smos", "--help"]
