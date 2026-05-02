import webview
import parser
import base64
import io
import traceback
import os
import sys

# Get the directory of the script to serve the correct frontend path
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
else:
    # Running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

class Api:
    def __init__(self, window):
        self.window = window

    def select_file(self):
        """Native file dialog fallback if drag-and-drop fails"""
        file_types = ('PDF Files (*.pdf)', 'All files (*.*)')
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return result[0]
        return None

    def analyze_pdf(self, b64_data, password):
        """Receives base64 PDF data from the frontend, analyzes it, and returns the JSON dashboard."""
        try:
            if not b64_data:
                return {"success": False, "error": "No file data received."}
                
            pdf_bytes = base64.b64decode(b64_data)
            pdf_file = io.BytesIO(pdf_bytes)
            
            # Use our pure Python parser
            dashboard_data = parser.parse_mpesa_statement(pdf_file, password)
            return {"success": True, "data": dashboard_data}
            
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

    def open_new_window(self):
        """Opens a new window of the application."""
        frontend_dir = os.path.join(bundle_dir, 'frontend')
        entry_html = os.path.join(frontend_dir, 'index.html')
        
        # We need a new API instance for the new window
        new_api = Api(None)
        new_window = webview.create_window(
            'M-Pesa Analytics (New)', 
            url=entry_html,
            js_api=new_api,
            width=1200,
            height=800,
            min_size=(900, 600),
            background_color='#0c1220'
        )
        new_api.window = new_window

if __name__ == '__main__':
    frontend_dir = os.path.join(bundle_dir, 'frontend')
    entry_html = os.path.join(frontend_dir, 'index.html')
    
    api = Api(None)
    window = webview.create_window(
        'M-Pesa Analytics', 
        url=entry_html,
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        background_color='#0c1220'
    )
    api.window = window
    webview.start(debug=False)
