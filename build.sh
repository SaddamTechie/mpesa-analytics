#!/bin/bash
echo "Building M-Pesa Analytics for Linux/Mac..."
# Bundle the app, hide the console window, name the output, and add frontend data
./.venv310/bin/python -m PyInstaller --noconfirm MPesaAnalytics.spec

echo "Build complete! Check the dist/ directory."
