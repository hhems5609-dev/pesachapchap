import http.server
import socketserver
import os

# Get the port Render gives us (default to 10000)
PORT = int(os.environ.get("PORT", 10000))

class PesaHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 1. Home Page (What people see first)
        if self.path == '/':
            self.path = 'index.html'
            
        # 2. Play Page (The game screen)
        elif self.path == '/play':
            self.path = 'play.html'
            
        # 3. Admin Panel (The one we just created)
        elif self.path == '/admin':
            self.path = 'admin.html'
        
        # 4. Handle anything else (CSS, JS, Images)
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), PesaHandler) as httpd:
        print(f"🚀 SERVER UPDATED")
        print(f"🔗 Routes: /, /play, /admin")
        httpd.serve_forever()
