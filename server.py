import http.server
import socketserver
import os

# Port assigned by Render
PORT = int(os.environ.get("PORT", 10000))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Route mapping
        if self.path == '/':
            self.path = 'index.html'
        elif self.path == '/play':
            self.path = 'play.html'
        elif self.path == '/admin':
            self.path = 'admin.html'
        
        # This part ensures the server actually finds the file
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    # Standard server startup
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"🚀 PESA CHAPCHAP LIVE ON PORT {PORT}")
        httpd.serve_forever()
