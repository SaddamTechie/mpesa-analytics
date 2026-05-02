#!/bin/bash
echo "Building M-Pesa Analytics for Linux/Mac..."
# Bundle the app, hide the console window, name the output, and add frontend data
uv run pyinstaller --noconfirm --onedir --windowed \
  --name "MPesaAnalytics" \
  --add-data "frontend:frontend" \
  --hidden-import "parser" \
  --hidden-import "PyQt5" \
  --hidden-import "PyQtWebEngine" \
  --hidden-import "qtpy" \
  app.py

echo "Build complete! Check the dist/ directory."
