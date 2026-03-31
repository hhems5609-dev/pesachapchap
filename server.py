import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 10000))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Route logic
        if self.path == '/':
            self.path = 'templates/index.html'
        elif self.path == '/play':
            self.path = 'templates/play.html'
        
        # If the file isn't in root, check templates
        if not os.path.exists(self.path.lstrip('/')):
            temp_path = os.path.join('templates', self.path.lstrip('/'))
            if os.path.exists(temp_path):
                self.path = temp_path

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
        print(f"🚀 SERVER LIVE ON PORT {PORT}")
        httpd.serve_forever()
