@echo off
echo Building M-Pesa Analytics for Windows...
uv run pyinstaller --noconfirm --onedir --windowed ^
  --name "MPesaAnalytics" ^
  --add-data "frontend;frontend" ^
  --hidden-import "parser" ^
  --hidden-import "PyQt5" ^
  --hidden-import "PyQtWebEngine" ^
  --hidden-import "qtpy" ^
  app.py

echo Build complete! Check the dist/ directory.
pause
