# M-Pesa Intelligence Desktop

A lightweight, privacy-first desktop application for analyzing M-Pesa statements. Transform your PDF statements into actionable financial insights with zero data leaving your machine.

## 🚀 Features

- **100% Offline & Private**: All parsing is done locally in-memory. No financial data is ever uploaded or stored.
- **Pure Python Engine**: Powered by a custom-built parser (no heavy `pandas` dependency), making it extremely fast and lightweight.
- **Modern Dashboard**: Visualize your spending, income, and cash flow patterns through an interactive UI.
- **Deep Insights**: Automatically identifies top recipients, monthly trends, and spending categories.
- **Portable**: Compiled into a single executable—runs without needing Python installed.

## 🛠️ Project Structure

- `app.py`: The native desktop entry point (using `pywebview`).
- `parser.py`: The "brain" of the app—handles PDF extraction and financial analysis.
- `frontend/`: contains the dashboard's HTML, CSS, and interactive Javascript.
- `build.sh` / `build.bat`: Scripts for one-click compilation using PyInstaller.

## 💻 Development Setup

1. **Install dependencies**:
   ```bash
   uv pip install pywebview pdfplumber PyQt5 PyQtWebEngine qtpy
   ```

2. **Run locally**:
   ```bash
   python app.py
   ```

## 📦 Building the Executable

To bundle the application into a standalone folder for distribution:

- **Linux/Mac**: 
  ```bash
  ./build.sh
  ```
- **Windows**: 
  ```bash
  build.bat
  ```

The final application will be available in the `dist/MPesaAnalytics/` directory.

## 🔒 Security
The app requires your M-Pesa PDF password (usually your ID number) to decrypt the statement. This password is used only for the current session and is never saved.
