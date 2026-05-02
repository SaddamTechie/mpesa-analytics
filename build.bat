@echo off
echo Building M-Pesa Analytics for Windows...
uv run pyinstaller --noconfirm --onefile --windowed ^
  --name "MPesaAnalytics" ^
  --add-data "frontend;frontend" ^
  --hidden-import "parser" ^
  --hidden-import "clr" ^
  --exclude-module "pandas" ^
  --exclude-module "numpy" ^
  --exclude-module "matplotlib" ^
  --exclude-module "PyQt5" ^
  --exclude-module "PyQtWebEngine" ^
  --exclude-module "PySide2" ^
  --exclude-module "PySide6" ^
  --exclude-module "tkinter" ^
  app.py

echo Build complete! Check the dist/ directory.
pause
