import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CHARTS_DIR = Path(os.getenv("CHARTS_DIR", str(Path(__file__).parent / "charts")))
HOST = os.getenv("CHARTS_HOST", "0.0.0.0")
PORT = int(os.getenv("CHARTS_PORT", "8001"))


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    handler = partial(CORSRequestHandler, directory=str(CHARTS_DIR))
    server = ThreadingHTTPServer((HOST, PORT), handler)

    print(f"Serving charts from {CHARTS_DIR}")
    print(f"http://{HOST}:{PORT}")

    server.serve_forever()
