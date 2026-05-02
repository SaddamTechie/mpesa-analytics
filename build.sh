#!/bin/bash
echo "Building M-Pesa Analytics for Linux/Mac..."
# Bundle the app, hide the console window, name the output, and add frontend data
./.venv310/bin/python -m PyInstaller --noconfirm --onefile --windowed \
  --name "MPesaAnalytics" \
  --add-data "frontend:frontend" \
  --hidden-import "parser" \
  --hidden-import "gi" \
  --hidden-import "appdirs" \
  --hidden-import "pkg_resources" \
  --exclude-module "pandas" \
  --exclude-module "numpy" \
  --exclude-module "matplotlib" \
  --exclude-module "PyQt5" \
  --exclude-module "PyQtWebEngine" \
  --exclude-module "PySide2" \
  --exclude-module "PySide6" \
  --exclude-module "tkinter" \
  app.py

echo "Build complete! Check the dist/ directory."
