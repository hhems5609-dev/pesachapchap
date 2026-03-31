import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 10000))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 1. Handle the root Home Page
        if self.path == '/':
            self.path = 'templates/index.html'
        
        # 2. Handle the Play Page specifically
        elif self.path == '/play':
            self.path = 'templates/play.html'
            
        # 3. For everything else (css, js, images), let SimpleHTTPRequestHandler 
        # look in the current folder, templates, or static.
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
        print(f"🚀 Pesa ChapChap Fully Loaded on {PORT}")
        httpd.serve_forever()
