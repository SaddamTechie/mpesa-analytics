@echo off
echo Building M-Pesa Analytics for Windows...
uv run pyinstaller --noconfirm MPesaAnalytics.spec

echo Build complete! Check the dist/ directory.
pause
