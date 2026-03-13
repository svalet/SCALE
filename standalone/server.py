import http.server
import os

PORT = int(os.environ.get('PORT', 8080))

handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map.update({'.js': 'application/javascript'})

with http.server.HTTPServer(('', PORT), handler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()
