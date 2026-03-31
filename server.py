import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 10000))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Professional Routing
        routes = {
            '/': 'index.html',
            '/play': 'play.html',
            '/admin': 'admin.html',
            '/deposit': 'deposit.html',
            '/sports': 'sports.html'
        }
        
        if self.path in routes:
            self.path = routes[self.path]
            
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"🚀 PESA HUB LIVE ON {PORT}")
        httpd.serve_forever()
