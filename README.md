# 💸 MpesaAnalytics

A privacy-first desktop application for analyzing M-Pesa statements. Transform your messy PDF statements into beautiful, actionable financial intelligence with zero data leaving your machine.

![MpesaAnalytics Dashboard](frontend/screenshot_placeholder.png)

## 🌟 Key Features

- **100% Offline & Private**: All parsing is done locally in-memory. Your financial data never touches a server or a database.
- **Synthesized Intelligence**: Features a high-fidelity "Intelligence" dashboard with glassmorphism aesthetics and Safaricom-themed branding.
- **Ultra-Lightweight**: Optimized to ~59MB by using native OS webview engines instead of bundling a whole browser.
- **Zero-Data Retention**: Every trace of your statement is wiped from memory as soon as you close the window.
- **Multi-Platform**: Native support for both Windows (WebView2) and Linux (WebKitGTK).

## 🚀 Getting Started

### For Users
Simply head to the [Releases](https://github.com/SaddamTechie/mpesa_analytics/releases) page and download the version for your OS:
- **Windows**: `MpesaAnalytics_Windows.exe`
- **Linux**: `MpesaAnalytics_Linux` (Mark as executable: `chmod +x MpesaAnalytics_Linux`)

### For Developers

1. **Setup Environment**:
   ```bash
   uv venv --python 3.10 --system-site-packages .venv310
   source .venv310/bin/activate
   uv pip install pywebview pdfplumber pyinstaller appdirs setuptools
   ```

2. **Run Locally**:
   ```bash
   python app.py
   ```

## 🛠️ Building & Distribution

We use a highly optimized build process that strips unnecessary assets (icons, themes, etc.) to keep the binary small.

- **Automated Build**: This repo is configured with GitHub Actions. Simply push a version tag to trigger a transparent, verified build:
  ```bash
  git tag v1.0
  git push origin v1.0
  ```
- **Local Build**:
  ```bash
  ./build.sh  # Linux
  build.bat   # Windows
  ```

## 🔒 Privacy & Security
The app requires your M-Pesa PDF password  to decrypt the statement. 
- **Encryption**: The password is used only for the local decryption session.
- **Transparency**: The build process is automated on GitHub Actions, so you can verify that the code in the binary matches the source code here.
- **Clean Exit**: The app calls an explicit `sys.exit(0)` on close to ensure no background processes or cached memory remain.

---
*Built with ❤️ for privacy and financial clarity.*
