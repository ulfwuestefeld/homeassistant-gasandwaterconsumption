ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Tesseract OCR, libheif, and pip packages
RUN apk add --no-cache tesseract-ocr dos2unix py3-pip libheif
RUN pip3 install --no-cache-dir aiosqlite pillow-heif

# Copy the custom integration files
COPY custom_components /usr/share/custom_components

# Copy startup script and fix line endings (Windows -> Linux)
COPY run.sh /
RUN dos2unix /run.sh && chmod a+x /run.sh

CMD ["/run.sh"]
