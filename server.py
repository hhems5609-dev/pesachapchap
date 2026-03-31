import http.server
import socketserver
import os
import sys

# Get port from Render
PORT = int(os.environ.get("PORT", 10000))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Use relative path for Render
            self.path = 'templates/index.html'
        try:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            print(f"Error serving request: {e}")

if __name__ == "__main__":
    try:
        socketserver.TCPServer.allow_reuse_address = True
        # Using 0.0.0.0 is mandatory for Render
        with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
            print(f"🚀 Pesa ChapChap starting on port {PORT}...")
            httpd.serve_forever()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
