#!/bin/bash

set -e

# Directorios del proyecto
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
BUILD_DIR="$PROJECT_ROOT/build/lambda"

# Limpiamos el build anterior
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Instalamos las dependencias del backend dentro del paquete de Lambda.
# AWS Lambda ejecutará Python 3.12 sobre Linux x86_64.
pip install \
  -r "$BACKEND_DIR/requirements.txt" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "$BUILD_DIR"

# Copiamos nuestro código Python
cp "$BACKEND_DIR/app.py" "$BUILD_DIR/"
cp "$BACKEND_DIR/lambda_function.py" "$BUILD_DIR/"
cp -R "$BACKEND_DIR/services" "$BUILD_DIR/"

echo "Build de Lambda preparado en: $BUILD_DIR"