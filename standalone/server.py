import http.server
import os

PORT = int(os.environ.get("PORT", 8080))


class StandaloneHandler(http.server.SimpleHTTPRequestHandler):
    """Serve static files; disable caching so CSS/JS updates show up without hard refresh."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
    }

    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path.endswith((".html", ".css", ".js")):
            self.send_header("Cache-Control", "no-store, max-age=0, must-revalidate")
        super().end_headers()


with http.server.HTTPServer(("", PORT), StandaloneHandler) as httpd:
    print(f"Serving on port {PORT}")
    httpd.serve_forever()
