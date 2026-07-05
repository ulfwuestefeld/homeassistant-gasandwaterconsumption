## Use buildx-provided TARGETARCH to pick the correct base image for
## the target architecture. This makes the image self-contained and
## avoids relying on external build metadata.
ARG BUILD_FROM
ARG BUILD_ARCH
ARG TARGETARCH
# Prefer Supervisor-provided BUILD_FROM when available.
# If not provided, prefer an image derived from the supervisor's
# `BUILD_ARCH` when available (Supervisor passes e.g. `aarch64`) and
# otherwise fall back to `TARGETARCH` (buildx-provided, e.g. `arm64`).
# Use the first available of these values to construct the fallback
# base image name for Home Assistant's ghcr images.
FROM ${BUILD_FROM:-ghcr.io/home-assistant/${BUILD_ARCH:-${TARGETARCH}}-base:latest}


# Install runtime dependencies
RUN apk add --no-cache tesseract-ocr tesseract-ocr-data-eng tesseract-ocr-data-deu dos2unix libheif

# Install build dependencies, pip packages, then clean up build deps
RUN apk add --no-cache --virtual .build-deps \
        py3-pip build-base libheif-dev python3-dev \
    && pip3 install --no-cache-dir --break-system-packages \
        aiosqlite pillow-heif \
    && apk del .build-deps

# Copy the custom integration files
COPY custom_components /usr/share/custom_components

# Copy startup script and fix line endings (Windows -> Linux)
COPY run.sh /
RUN dos2unix /run.sh && chmod a+x /run.sh

CMD ["/run.sh"]
