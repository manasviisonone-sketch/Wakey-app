import http.server
import socketserver

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

Handler = MyHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🚀 Frontend server running at http://localhost:{PORT}")
    print(f"📂 Serving files from: {httpd.server_address}")
    print("\n✅ Open http://localhost:8000 in your browser")
    print("⏰ Backend should be running on http://localhost:3001\n")
    httpd.serve_forever()