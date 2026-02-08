ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Tesseract OCR for optional meter photo reading
RUN apk add --no-cache tesseract-ocr

# Copy the custom integration files
COPY custom_components /usr/share/custom_components

# Copy startup script
COPY run.sh /
RUN chmod a+x /run.sh

CMD ["/run.sh"]
