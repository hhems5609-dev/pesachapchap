import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 10000))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # If they ask for /, give them index.html
        if self.path == '/':
            self.path = 'index.html'
        # If they ask for /play, give them play.html
        elif self.path == '/play':
            self.path = 'play.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), MyHandler) as httpd:
        print(f"🚀 Pesa ChapChap Brute Force Mode on {PORT}")
        httpd.serve_forever()
