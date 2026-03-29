from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8080

Handler = SimpleHTTPRequestHandler

with HTTPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()
