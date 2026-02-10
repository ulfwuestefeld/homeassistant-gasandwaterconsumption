# Tesseract Training Data (tessdata)

Place custom Tesseract `.traineddata` files in this directory to improve
meter reading OCR accuracy.

## How it works

When this directory contains at least one `.traineddata` file, the integration
will pass it to Tesseract via the `--tessdata-dir` option, **overriding** the
system-installed training data. If the directory is empty, the system default
tessdata is used as a fallback.

## Recommended files

| File | Description |
|------|-------------|
| `eng.traineddata` | English language data (digits, labels) |
| `deu.traineddata` | German language data (for labels like "Zaehler") |
| `custom.traineddata` | Your own fine-tuned model for meter displays |

## Where to get training data

- **Standard models**: https://github.com/tesseract-ocr/tessdata
- **Best (slower) models**: https://github.com/tesseract-ocr/tessdata_best
- **Fast models**: https://github.com/tesseract-ocr/tessdata_fast
- **Custom training**: https://tesseract-ocr.github.io/tessdoc/tess4/TrainingTesseract-4.00.html

## Tips for meter reading accuracy

- The `tessdata_best` models generally give better digit recognition than the
  default `tessdata_fast` variants shipped with most Linux packages.
- For optimal results with gas/water meter displays, consider training a
  custom model on images of your specific meter type.
- Only place files here that you actually need -- each `.traineddata` file adds
  to the integration's size.
