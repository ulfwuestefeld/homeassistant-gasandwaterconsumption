## Use buildx-provided TARGETARCH to pick the correct base image for
## the target architecture. This makes the image self-contained and
## avoids relying on external build metadata.
ARG TARGETARCH
FROM ghcr.io/home-assistant/${TARGETARCH}-base:latest


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
